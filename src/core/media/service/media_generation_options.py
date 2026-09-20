"""Normalize Automedia / Google Flow generation options for Gemini image and Veo."""

from __future__ import annotations

from typing import Any

IMAGE_ASPECTS = frozenset({"16:9", "4:3", "1:1", "3:4", "9:16"})
VIDEO_ASPECTS = frozenset({"16:9", "9:16"})
VIDEO_DURATIONS = frozenset({4, 6, 8, 10})
VIDEO_RESOLUTIONS = frozenset({"720p", "360p"})


def normalize_image_aspect(value: str | None) -> str | None:
    raw = (value or "").strip()
    return raw if raw in IMAGE_ASPECTS else None


def normalize_video_aspect(value: str | None) -> str | None:
    raw = (value or "").strip()
    if raw in VIDEO_ASPECTS:
        return raw
    if raw in {"4:3", "1:1"}:
        return "16:9"
    if raw in {"3:4"}:
        return "9:16"
    return None


def normalize_duration(value: int | None) -> int | None:
    if value is None:
        return None
    if value in VIDEO_DURATIONS:
        # Veo 3.x accepts 4/6/8; map 10s down to 8s.
        return 8 if value == 10 else value
    return None


def normalize_resolution(value: str | None) -> str | None:
    raw = (value or "").strip().lower()
    if raw == "720p":
        return "720p"
    if raw == "360p":
        return "720p"
    return None


def media_kind_for(kind: str | None, default: str) -> str:
    raw = (kind or "").strip().lower()
    if raw in {"character", "image"}:
        return "image"
    if raw in {"scene", "video"}:
        return "video"
    return default


def kind_brief(kind: str | None) -> str:
    raw = (kind or "").strip().lower()
    if raw == "character":
        return (
            "Create a reusable character reference: consistent face, outfit, and identity. "
            "Plain or simple background. Suitable for reuse across later scenes."
        )
    if raw == "scene":
        return (
            "Create a cinematic scene / establishing shot suitable for a marketing film sequence. "
            "Clear subject, lighting, and camera language."
        )
    return ""


def apply_kind_brief(prompt: str, kind: str | None) -> str:
    brief = kind_brief(kind)
    if not brief:
        return prompt
    return f"{prompt.rstrip()}\n\n{brief}"


def image_generation_config(aspect_ratio: str | None) -> dict[str, Any]:
    config: dict[str, Any] = {"responseModalities": ["TEXT", "IMAGE"]}
    ratio = normalize_image_aspect(aspect_ratio)
    if ratio:
        config["imageConfig"] = {"aspectRatio": ratio}
    return config


def veo_parameters(
    *,
    aspect_ratio: str | None = None,
    duration_seconds: int | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    ratio = normalize_video_aspect(aspect_ratio)
    if ratio:
        params["aspectRatio"] = ratio
    duration = normalize_duration(duration_seconds)
    if duration:
        params["durationSeconds"] = duration
    res = normalize_resolution(resolution)
    if res:
        params["resolution"] = res
    return params
