from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CLIPS = 12
MAX_CLIP_BYTES = 80 * 1024 * 1024
DOWNLOAD_TIMEOUT = 120.0


class VideoConcatError(RuntimeError):
    pass


def output_size(aspect_ratio: str | None) -> tuple[int, int]:
    if (aspect_ratio or "").strip() in {"9:16", "9/16", "portrait"}:
        return 720, 1280
    return 1280, 720


def build_filter_graph(count: int, width: int, height: int, with_audio: bool) -> str:
    parts: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []
    for index in range(count):
        video = f"v{index}"
        parts.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[{video}]"
        )
        video_labels.append(f"[{video}]")
        if with_audio:
            audio = f"a{index}"
            parts.append(
                f"[{index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[{audio}]"
            )
            audio_labels.append(f"[{audio}]")
    joined_v = "".join(video_labels)
    if with_audio:
        joined_a = "".join(audio_labels)
        parts.append(f"{joined_v}{joined_a}concat=n={count}:v=1:a=1[vout][aout]")
    else:
        parts.append(f"{joined_v}concat=n={count}:v=1:a=0[vout]")
    return ";".join(parts)


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise VideoConcatError("FFmpeg is not installed on the server. Install ffmpeg to assemble scenes.")
    return path


def _has_audio(ffprobe: str | None, path: str) -> bool:
    binary = ffprobe or shutil.which("ffprobe")
    if not binary:
        return False
    result = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return bool(result.stdout.strip())


async def _download(url: str, dest: Path) -> None:
    import httpx

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                detail = (await response.aread()).decode(errors="replace")[:400]
                raise VideoConcatError(f"Could not download a scene clip ({response.status_code}): {detail}")
            written = 0
            with dest.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > MAX_CLIP_BYTES:
                        raise VideoConcatError("A scene clip is too large to assemble.")
                    handle.write(chunk)
            if written < 32:
                raise VideoConcatError("A scene clip downloaded empty.")


def _run_ffmpeg(ffmpeg: str, inputs: list[str], output: str, graph: str, with_audio: bool) -> None:
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for path in inputs:
        command.extend(["-i", path])
    command.extend(["-filter_complex", graph, "-map", "[vout]"])
    if with_audio:
        command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "128k"])
    else:
        command.append("-an")
    command.extend(["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output])
    result = subprocess.run(command, capture_output=True, text=True, timeout=240, check=False)
    if result.returncode != 0 or not os.path.isfile(output) or os.path.getsize(output) < 32:
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()[:800]
        raise VideoConcatError(detail or "Could not assemble the scene video.")


def _upload(path: str) -> str:
    from core.cloudstorage.service.storageservice import StorageService

    storage = StorageService()
    object_name = f"{uuid.uuid4().hex}.mp4"
    with open(path, "rb") as handle:
        return storage.upload_file(
            handle,
            object_name,
            content_type="video/mp4",
            timeout_seconds=300,
            folder="generated-videos",
        )


async def concat_video_urls(urls: list[str], aspect_ratio: str | None = "16:9") -> str:
    cleaned = [str(url).strip() for url in urls if str(url).strip()]
    if len(cleaned) < 1:
        raise VideoConcatError("Add at least one generated clip before assembling.")
    if len(cleaned) > MAX_CLIPS:
        raise VideoConcatError(f"Scene builder can assemble at most {MAX_CLIPS} clips.")
    if len(cleaned) == 1:
        return cleaned[0]

    ffmpeg = require_ffmpeg()
    width, height = output_size(aspect_ratio)
    work = tempfile.mkdtemp(prefix="automedia-concat-")
    try:
        inputs: list[str] = []
        for index, url in enumerate(cleaned):
            dest = Path(work) / f"clip-{index}.mp4"
            await _download(url, dest)
            inputs.append(str(dest))
        audio = all(_has_audio(None, path) for path in inputs)
        graph = build_filter_graph(len(inputs), width, height, audio)
        output = str(Path(work) / "scene.mp4")
        _run_ffmpeg(ffmpeg, inputs, output, graph, audio)
        return _upload(output)
    finally:
        shutil.rmtree(work, ignore_errors=True)
