"""Shared helpers for product image vs video URLs."""

_VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".webm", ".avi")


def media_looks_like_video(url: str) -> bool:
    path = (url or "").split("?", 1)[0].lower()
    return any(path.endswith(ext) for ext in _VIDEO_SUFFIXES) or ".mp4" in path


def split_media_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    photos: list[str] = []
    videos: list[str] = []
    for url in urls:
        cleaned = (url or "").strip()
        if not cleaned:
            continue
        if media_looks_like_video(cleaned):
            videos.append(cleaned)
        else:
            photos.append(cleaned)
    return photos, videos
