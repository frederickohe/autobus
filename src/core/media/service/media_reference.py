"""Resolve optional reference image/video bytes for media generation."""

from __future__ import annotations

import base64
import logging
from typing import Protocol
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_REFERENCE_BYTES = 20 * 1024 * 1024
_ALLOWED_SCHEMES = {"http", "https"}


class MediaReferenceError(ValueError):
    pass


class GenerationReferenceSource(Protocol):
    reference_base64: str | None
    reference_mime_type: str | None
    reference_url: str | None


def clean_base64(value: str | None) -> tuple[str | None, str]:
    """
    Strip a data-URL prefix and whitespace.

    Returns (mime_from_data_url_or_None, raw_base64).
    """
    raw = (value or "").strip()
    if not raw:
        return None, ""
    mime = None
    if raw.startswith("data:") and "," in raw:
        header, raw = raw.split(",", 1)
        meta = header[5:]
        if ";" in meta:
            mime = meta.split(";", 1)[0].strip() or None
        elif meta.strip():
            mime = meta.strip() or None
    compact = "".join(raw.split())
    return mime, compact


def infer_mime(hint: str | None, fallback: str = "image/jpeg") -> str:
    value = (hint or "").strip().lower()
    if "/" in value and not value.startswith("http"):
        return value.split(";", 1)[0].strip() or fallback
    lowered = value.rsplit("?", 1)[0]
    if lowered.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".gif"):
        return "image/gif"
    if lowered.endswith(".bmp"):
        return "image/bmp"
    if lowered.endswith(".mp4"):
        return "video/mp4"
    if lowered.endswith(".mov"):
        return "video/quicktime"
    if lowered.endswith(".webm"):
        return "video/webm"
    if lowered.endswith((".m4v",)):
        return "video/mp4"
    return fallback


def is_image_mime(mime: str) -> bool:
    return (mime or "").strip().lower().startswith("image/")


def is_video_mime(mime: str) -> bool:
    return (mime or "").strip().lower().startswith("video/")


def decode_reference_base64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=False)
    except Exception as e:
        raise MediaReferenceError("Reference media is not valid base64.") from e


async def fetch_reference_from_url(url: str) -> tuple[bytes, str]:
    import httpx

    parsed = urlparse(url.strip())
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        raise MediaReferenceError("Reference URL must be an http(s) URL.")

    timeout = httpx.Timeout(connect=20.0, read=90.0, write=30.0, pool=20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url.strip()) as resp:
                if resp.status_code >= 400:
                    raise MediaReferenceError(
                        f"Could not download reference media ({resp.status_code})."
                    )
                content_type = (resp.headers.get("content-type") or "").split(";", 1)[0].strip()
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_REFERENCE_BYTES:
                        raise MediaReferenceError(
                            "Reference media is too large (max 20 MB)."
                        )
                    chunks.append(chunk)
    except MediaReferenceError:
        raise
    except httpx.TimeoutException as e:
        raise MediaReferenceError("Timed out downloading the reference media.") from e
    except Exception as e:
        raise MediaReferenceError("Could not download the reference media.") from e

    raw = b"".join(chunks)
    if not raw:
        raise MediaReferenceError("Reference URL returned no data.")
    mime = infer_mime(content_type or url, fallback="application/octet-stream")
    return raw, mime


def validate_reference(raw: bytes, mime: str) -> None:
    if not raw:
        raise MediaReferenceError("Reference media is empty.")
    if len(raw) > MAX_REFERENCE_BYTES:
        raise MediaReferenceError("Reference media is too large (max 20 MB).")
    if not is_image_mime(mime) and not is_video_mime(mime):
        raise MediaReferenceError(
            "Reference must be an image or video file."
        )


async def resolve_generation_reference(
    req: GenerationReferenceSource,
) -> tuple[str, str] | None:
    """
    Return (base64, mime_type) for an optional generation reference, or None.
    """
    header_mime, cleaned = clean_base64(req.reference_base64)
    mime_hint = req.reference_mime_type or header_mime
    raw: bytes | None = None
    mime = infer_mime(mime_hint, fallback="")

    if cleaned:
        raw = decode_reference_base64(cleaned)
        if not mime:
            mime = infer_mime(header_mime, fallback="image/jpeg")
    elif (req.reference_url or "").strip():
        raw, fetched_mime = await fetch_reference_from_url(req.reference_url.strip())
        mime = infer_mime(mime_hint or fetched_mime, fallback=fetched_mime)

    if raw is None:
        return None

    if not mime:
        mime = "image/jpeg"
    validate_reference(raw, mime)
    encoded = base64.b64encode(raw).decode("ascii")
    logger.info(
        "[MEDIA_REF] Resolved %s reference (%s bytes)",
        mime,
        len(raw),
    )
    return encoded, mime


def reference_prompt_prefix(mime: str) -> str:
    kind = "video" if is_video_mime(mime) else "image"
    return (
        f"A reference {kind} is attached. Use it as visual guidance for subject, "
        "composition, branding, and style. Follow the creative brief for what to "
        "create or change.\n\n"
    )


def build_image_generate_payload(
    prompt: str,
    *,
    reference_base64: str | None = None,
    reference_mime_type: str | None = None,
) -> dict:
    """Gemini generateContent payload; optional inline reference image/video."""
    parts: list[dict] = [{"text": prompt}]
    header_mime, cleaned = clean_base64(reference_base64)
    if cleaned:
        mime = (reference_mime_type or header_mime or "image/png").strip() or "image/png"
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime,
                    "data": cleaned,
                }
            }
        )
    return {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }


def build_veo_instance(
    prompt: str,
    *,
    reference_base64: str | None = None,
    reference_mime_type: str | None = None,
) -> dict:
    """Veo predictLongRunning instance: text, optional first-frame image, or video."""
    instance: dict = {"prompt": prompt}
    header_mime, cleaned = clean_base64(reference_base64)
    if not cleaned:
        return instance
    mime = (reference_mime_type or header_mime or "image/jpeg").strip() or "image/jpeg"
    media = {"bytesBase64Encoded": cleaned, "mimeType": mime}
    if is_video_mime(mime):
        instance["video"] = media
    else:
        instance["image"] = media
    return instance
