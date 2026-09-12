"""Resolve optional reference image/video bytes for media generation."""

from __future__ import annotations

import base64
import logging
from typing import Protocol
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_REFERENCE_BYTES = 20 * 1024 * 1024
MAX_REFERENCES = 3
_ALLOWED_SCHEMES = {"http", "https"}


class MediaReferenceError(ValueError):
    pass


class GenerationReferenceItem(Protocol):
    base64: str | None
    mime_type: str | None
    url: str | None


class GenerationReferenceSource(Protocol):
    reference_base64: str | None
    reference_mime_type: str | None
    reference_url: str | None
    references: list[GenerationReferenceItem] | None


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


async def _resolve_one(
    *,
    reference_base64: str | None,
    reference_mime_type: str | None,
    reference_url: str | None,
) -> tuple[str, str] | None:
    header_mime, cleaned = clean_base64(reference_base64)
    mime_hint = reference_mime_type or header_mime
    raw: bytes | None = None
    mime = infer_mime(mime_hint, fallback="")

    if cleaned:
        raw = decode_reference_base64(cleaned)
        if not mime:
            mime = infer_mime(header_mime, fallback="image/jpeg")
    elif (reference_url or "").strip():
        raw, fetched_mime = await fetch_reference_from_url(reference_url.strip())
        mime = infer_mime(mime_hint or fetched_mime, fallback=fetched_mime)

    if raw is None:
        return None

    if not mime:
        mime = "image/jpeg"
    validate_reference(raw, mime)
    encoded = base64.b64encode(raw).decode("ascii")
    logger.info("[MEDIA_REF] Resolved %s reference (%s bytes)", mime, len(raw))
    return encoded, mime


async def resolve_generation_references(
    req: GenerationReferenceSource,
) -> list[tuple[str, str]]:
    """Return (base64, mime_type) pairs for every attached reference."""
    items: list[tuple[str | None, str | None, str | None]] = []
    extra = getattr(req, "references", None) or []
    for item in extra:
        items.append(
            (
                getattr(item, "base64", None),
                getattr(item, "mime_type", None),
                getattr(item, "url", None),
            )
        )
    if not items:
        items.append((req.reference_base64, req.reference_mime_type, req.reference_url))

    resolved: list[tuple[str, str]] = []
    for base64_value, mime_type, url in items:
        found = await _resolve_one(
            reference_base64=base64_value,
            reference_mime_type=mime_type,
            reference_url=url,
        )
        if found:
            resolved.append(found)

    if len(resolved) > MAX_REFERENCES:
        raise MediaReferenceError(
            f"You can attach up to {MAX_REFERENCES} reference files."
        )
    return resolved


async def resolve_generation_reference(
    req: GenerationReferenceSource,
) -> tuple[str, str] | None:
    refs = await resolve_generation_references(req)
    return refs[0] if refs else None


def reference_prompt_prefix(references: list[tuple[str, str]]) -> str:
    if not references:
        return ""
    images = sum(1 for _, mime in references if is_image_mime(mime))
    videos = sum(1 for _, mime in references if is_video_mime(mime))
    bits = []
    if images:
        bits.append(f"{images} reference image{'s' if images != 1 else ''}")
    if videos:
        bits.append(f"{videos} reference video{'s' if videos != 1 else ''}")
    attached = " and ".join(bits) if bits else "reference media"
    return (
        f"{attached.capitalize()} {'are' if (images + videos) != 1 else 'is'} attached. "
        "Use them as visual guidance for subject, composition, branding, and style. "
        "Follow the creative brief for what to create or change.\n\n"
    )


def _normalized_refs(
    *,
    references: list[tuple[str, str]] | None,
    reference_base64: str | None,
    reference_mime_type: str | None,
) -> list[tuple[str, str]]:
    if references:
        return references
    header_mime, cleaned = clean_base64(reference_base64)
    if not cleaned:
        return []
    mime = (reference_mime_type or header_mime or "image/png").strip() or "image/png"
    return [(cleaned, mime)]


def build_image_generate_payload(
    prompt: str,
    *,
    references: list[tuple[str, str]] | None = None,
    reference_base64: str | None = None,
    reference_mime_type: str | None = None,
) -> dict:
    """Gemini generateContent payload; optional inline reference images/videos."""
    parts: list[dict] = [{"text": prompt}]
    for raw_b64, mime in _normalized_refs(
        references=references,
        reference_base64=reference_base64,
        reference_mime_type=reference_mime_type,
    ):
        header_mime, cleaned = clean_base64(raw_b64)
        if not cleaned:
            continue
        parts.append(
            {
                "inlineData": {
                    "mimeType": (mime or header_mime or "image/png").strip() or "image/png",
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
    references: list[tuple[str, str]] | None = None,
    reference_base64: str | None = None,
    reference_mime_type: str | None = None,
) -> dict:
    """
    Veo instance: text plus optional first-frame / reference images.

    User-uploaded videos are not sent as ``video`` — Veo extension only accepts
    a URI from a previous Veo output, and sending bytes leaves an empty result.
    """
    instance: dict = {"prompt": prompt}
    refs = _normalized_refs(
        references=references,
        reference_base64=reference_base64,
        reference_mime_type=reference_mime_type,
    )
    images: list[dict] = []
    for raw_b64, mime in refs:
        header_mime, cleaned = clean_base64(raw_b64)
        if not cleaned or is_video_mime(mime or header_mime or ""):
            continue
        images.append(
            {
                "bytesBase64Encoded": cleaned,
                "mimeType": (mime or header_mime or "image/jpeg").strip() or "image/jpeg",
            }
        )
    if not images:
        return instance
    if len(images) == 1:
        instance["image"] = images[0]
        return instance
    instance["referenceImages"] = [
        {"image": image, "referenceType": "asset"} for image in images[:MAX_REFERENCES]
    ]
    return instance


def build_veo_payload(
    prompt: str,
    *,
    references: list[tuple[str, str]] | None = None,
    reference_base64: str | None = None,
    reference_mime_type: str | None = None,
) -> dict:
    return {
        "instances": [
            build_veo_instance(
                prompt,
                references=references,
                reference_base64=reference_base64,
                reference_mime_type=reference_mime_type,
            )
        ],
        "parameters": {
            "sampleCount": 1,
            "durationSeconds": 8,
        },
    }
