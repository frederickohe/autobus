from __future__ import annotations

from pydantic import BaseModel, Field


class VideoConcatRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=12)
    aspect_ratio: str | None = "16:9"


class VideoConcatResponse(BaseModel):
    video_url: str
    clip_count: int
