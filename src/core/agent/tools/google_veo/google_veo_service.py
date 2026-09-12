from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from dotenv import load_dotenv

from core.cloudstorage.service.storageservice import StorageService
from core.media.service.veo_operation import (
    VeoVideoResult,
    extract_video_from_operation,
    missing_video_error,
)

_env_path = Path(__file__).resolve().parents[5] / ".env"
load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger(__name__)


class GoogleVeoGenerationError(RuntimeError):
    pass


class GoogleVeoTimeoutError(GoogleVeoGenerationError):
    """Raised when Veo video generation does not complete in time."""

    pass


class GoogleVeoService:
    """
    Veo video generation via Google's Generative Language REST API.

    Veo is asynchronous: POST :predictLongRunning, then poll the operation until done.

    Env vars:
    - GOOGLE_API_KEY
    - VEO_GENERATE_URL (base URL, typically https://generativelanguage.googleapis.com/v1beta)
    - VEO_MODEL (e.g. veo-3.1-generate-preview)
    - VEO_USE_X_GOOG_API_KEY (default false)
    - VEO_POLL_INTERVAL_SECONDS (default 10)
    - VEO_MAX_POLL_SECONDS (default 600)
    """

    def __init__(self) -> None:
        self._api_key = os.environ.get("GOOGLE_API_KEY", "")
        self._base_url = os.environ.get("VEO_GENERATE_URL", "").rstrip("/")
        self._model = os.environ.get("VEO_MODEL", "").strip()
        self._use_x_goog = os.environ.get("VEO_USE_X_GOOG_API_KEY", "false").lower() == "true"
        self._poll_interval = float(os.environ.get("VEO_POLL_INTERVAL_SECONDS", "10"))
        self._max_poll_seconds = float(os.environ.get("VEO_MAX_POLL_SECONDS", "600"))

        if not self._api_key:
            raise GoogleVeoGenerationError("GOOGLE_API_KEY is not set")
        if not self._base_url:
            raise GoogleVeoGenerationError("VEO_GENERATE_URL is not set")
        if not self._model:
            raise GoogleVeoGenerationError("VEO_MODEL is not set")

        self._start_url = f"{self._base_url}/models/{self._model}:predictLongRunning"

    def _auth(self) -> tuple[dict[str, str], dict[str, str]]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        params: dict[str, str] = {}
        if self._use_x_goog:
            headers["x-goog-api-key"] = self._api_key
        else:
            params["key"] = self._api_key
        return headers, params

    def _binary_download_request(self, source_url: str) -> tuple[str, dict[str, str]]:
        """
        Build URL + headers for downloading generated media.

        The Files API requires ``alt=media`` on ``.../files/{id}:download``.
        Using JSON Accept/Content-Type on this GET often yields 400 from Google.
        """
        raw = source_url.strip()
        if "://" not in raw:
            raw = f"{self._base_url.rstrip('/')}/{raw.lstrip('/')}"
        parsed = urlparse(raw)

        path = parsed.path or ""
        is_files = "/files/" in path
        if is_files and ":download" not in path:
            path = path.rstrip("/") + ":download"

        q_existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
        q_existing.pop("key", None)

        headers: dict[str, str] = {"Accept": "*/*"}
        query_parts = dict(q_existing)
        if is_files:
            query_parts["alt"] = "media"
        if self._use_x_goog:
            headers["x-goog-api-key"] = self._api_key
        else:
            query_parts["key"] = self._api_key

        new_query = urlencode(list(query_parts.items()))
        clean = urlunparse(
            (parsed.scheme, parsed.netloc, path, parsed.params, new_query, parsed.fragment)
        )
        return clean, headers

    def _http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=30.0,
            read=max(self._max_poll_seconds, 120.0),
            write=120.0,
            pool=30.0,
        )

    async def generate_video_url(
        self,
        prompt: str,
        *,
        user_id: str | None = None,
        reference_base64: str | None = None,
        reference_mime_type: str | None = None,
        references: list[tuple[str, str]] | None = None,
    ) -> str:
        result = await self._generate_video_result(
            prompt,
            user_id=user_id,
            reference_base64=reference_base64,
            reference_mime_type=reference_mime_type,
            references=references,
        )
        if result.uri:
            return result.uri
        raise GoogleVeoGenerationError(missing_video_error(result))

    async def _generate_video_result(
        self,
        prompt: str,
        *,
        user_id: str | None = None,
        reference_base64: str | None = None,
        reference_mime_type: str | None = None,
        references: list[tuple[str, str]] | None = None,
    ) -> VeoVideoResult:
        # Veo does not accept arbitrary user_id on the request body.
        headers, params = self._auth()
        from core.media.service.media_reference import build_veo_payload

        payload = build_veo_payload(
            prompt,
            references=references,
            reference_base64=reference_base64,
            reference_mime_type=reference_mime_type,
        )

        timeout = self._http_timeout()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                start_resp = await client.post(
                    self._start_url,
                    headers=headers,
                    params=params,
                    json=payload,
                )
        except httpx.TimeoutException as e:
            raise GoogleVeoTimeoutError(
                "Google Veo API did not respond when starting video generation."
            ) from e

        if start_resp.status_code >= 400:
            raise GoogleVeoGenerationError(
                f"Google Veo API error {start_resp.status_code}: {start_resp.text}"
            )

        try:
            start_data = start_resp.json()
        except Exception as e:
            raise GoogleVeoGenerationError(f"Invalid JSON from Google Veo API: {e}") from e

        operation_name = start_data.get("name")
        if not isinstance(operation_name, str) or not operation_name.strip():
            raise GoogleVeoGenerationError(
                "Google Veo API did not return an operation name for polling."
            )

        operation_name = operation_name.strip().lstrip("/")
        poll_url = f"{self._base_url}/{operation_name}"

        elapsed = 0.0
        while elapsed < self._max_poll_seconds:
            await asyncio.sleep(self._poll_interval)
            elapsed += self._poll_interval

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    poll_resp = await client.get(poll_url, headers=headers, params=params)
            except httpx.TimeoutException as e:
                raise GoogleVeoTimeoutError(
                    "Google Veo API timed out while polling video generation status."
                ) from e

            if poll_resp.status_code >= 400:
                raise GoogleVeoGenerationError(
                    f"Google Veo poll error {poll_resp.status_code}: {poll_resp.text}"
                )

            try:
                poll_data = poll_resp.json()
            except Exception as e:
                raise GoogleVeoGenerationError(f"Invalid JSON from Google Veo poll: {e}") from e

            if poll_data.get("error"):
                raise GoogleVeoGenerationError(f"Google Veo generation failed: {poll_data['error']}")

            if poll_data.get("done"):
                result = extract_video_from_operation(poll_data)
                if result.has_media:
                    return result
                logger.warning(
                    "[VEO] Completed operation had no video media. keys=%s rai=%s",
                    list(poll_data.keys()),
                    result.rai_reason,
                )
                raise GoogleVeoGenerationError(missing_video_error(result))

        raise GoogleVeoTimeoutError(
            f"Google Veo video generation did not complete within {int(self._max_poll_seconds)} seconds."
        )

    async def generate_video_and_store(
        self,
        prompt: str,
        *,
        user_id: str | None = None,
        reference_base64: str | None = None,
        reference_mime_type: str | None = None,
        references: list[tuple[str, str]] | None = None,
    ) -> str:
        """
        Generates a video with Veo, downloads it, uploads to Contabo storage,
        and returns the Contabo URL (suitable for streaming by the frontend).
        """
        result = await self._generate_video_result(
            prompt,
            user_id=user_id,
            reference_base64=reference_base64,
            reference_mime_type=reference_mime_type,
            references=references,
        )
        if not result.has_media:
            raise GoogleVeoGenerationError(missing_video_error(result))

        suffix = ".mp4"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp_path = tmp.name

            if result.base64 and not result.uri:
                import base64

                with open(tmp_path, "wb") as f:
                    f.write(base64.b64decode(result.base64, validate=False))
            else:
                download_url, dl_headers = self._binary_download_request(result.uri or "")
                download_timeout = self._http_timeout()
                async with httpx.AsyncClient(
                    timeout=download_timeout, follow_redirects=True
                ) as client:
                    async with client.stream(
                        "GET",
                        download_url,
                        headers=dl_headers,
                    ) as r:
                        if r.status_code >= 400:
                            detail = (await r.aread()).decode(errors="replace")[:2000]
                            raise GoogleVeoGenerationError(
                                f"Failed to download generated video ({r.status_code}): {detail}"
                            )
                        with open(tmp_path, "wb") as f:
                            async for chunk in r.aiter_bytes():
                                if chunk:
                                    f.write(chunk)

            storage = StorageService()
            object_name = f"{uuid.uuid4().hex}{suffix}"
            with open(tmp_path, "rb") as f:
                contabo_url = storage.upload_file(
                    f,
                    object_name,
                    content_type="video/mp4",
                    timeout_seconds=300,
                    folder="generated-videos",
                )

            return contabo_url
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
