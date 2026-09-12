"""Parse completed Veo long-running operations for a downloadable video."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VeoVideoResult:
    uri: str | None = None
    base64: str | None = None
    rai_reason: str | None = None

    @property
    def has_media(self) -> bool:
        return bool((self.uri or "").strip() or (self.base64 or "").strip())


def looks_like_video_uri(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    lowered = raw.lower()
    if lowered.startswith(("http://", "https://", "gs://")):
        return True
    if lowered.startswith("files/") or "/files/" in lowered:
        return True
    return False


def rai_filter_reason(data: Any) -> str | None:
    reasons: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in (
                "raiMediaFilteredReasons",
                "rai_media_filtered_reasons",
                "raiFilteredReasons",
            ):
                raw = value.get(key)
                if isinstance(raw, list):
                    reasons.extend(str(item).strip() for item in raw if str(item).strip())
                elif isinstance(raw, str) and raw.strip():
                    reasons.append(raw.strip())
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(data)
    if not reasons:
        return None
    unique: list[str] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return "; ".join(unique)


def extract_video_from_operation(data: dict[str, Any]) -> VeoVideoResult:
    """
    Veo may return:
    - response.generateVideoResponse.generatedSamples[0].video.uri
    - the same samples directly under response
    - a relative Files API path (files/...)
    - inline bytesBase64Encoded instead of a URI
    - a completed-but-empty payload when RAI filters the result
    """
    rai = rai_filter_reason(data)
    uri, encoded = _extract_video_fields(data)
    return VeoVideoResult(uri=uri, base64=encoded, rai_reason=rai)


def missing_video_error(result: VeoVideoResult) -> str:
    if result.rai_reason:
        return (
            "Google Veo blocked this video. Try a different prompt or reference. "
            f"({result.rai_reason})"
        )
    return (
        "Google Veo finished but did not return a video. "
        "Try again, or generate without a video reference."
    )


def _extract_video_fields(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, str):
        text = value.strip()
        if looks_like_video_uri(text):
            return text, None
        return None, None

    if isinstance(value, dict):
        video = value.get("video")
        if isinstance(video, dict):
            uri, encoded = _media_from_dict(video)
            if uri or encoded:
                return uri, encoded
        uri, encoded = _media_from_dict(value)
        if uri or encoded:
            return uri, encoded
        for key in (
            "generateVideoResponse",
            "generate_video_response",
            "generatedSamples",
            "generated_samples",
            "response",
            "videos",
        ):
            nested = value.get(key)
            if nested is None:
                continue
            found_uri, found_b64 = _extract_video_fields(nested)
            if found_uri or found_b64:
                return found_uri, found_b64
        for nested in value.values():
            if nested is value:
                continue
            found_uri, found_b64 = _extract_video_fields(nested)
            if found_uri or found_b64:
                return found_uri, found_b64

    if isinstance(value, list):
        for nested in value:
            found_uri, found_b64 = _extract_video_fields(nested)
            if found_uri or found_b64:
                return found_uri, found_b64

    return None, None


def _media_from_dict(value: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in ("uri", "fileUri", "file_uri", "downloadUri", "download_uri"):
        raw = value.get(key)
        if isinstance(raw, str) and looks_like_video_uri(raw):
            return raw.strip(), None
    for key in ("bytesBase64Encoded", "bytes_base64_encoded", "data"):
        raw = value.get(key)
        if isinstance(raw, str) and len(raw.strip()) > 80:
            return None, raw.strip()
    return None, None
