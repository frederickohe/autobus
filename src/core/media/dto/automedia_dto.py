from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AutomediaClipDto(BaseModel):
    id: str
    url: str
    prompt: str = ""
    duration_sec: int | None = None


class AutomediaAssetDto(BaseModel):
    id: str
    campaign_id: str | None = None
    kind: str
    url: str
    prompt: str = ""
    name: str | None = None
    favorite: bool = False
    source: str = "generated"
    aspect: str = "16:9"
    duration_sec: int | None = None
    resolution: str | None = None
    clips: list[AutomediaClipDto] = Field(default_factory=list)
    created_at: int | None = None


class AutomediaAssetPatch(BaseModel):
    url: str | None = None
    prompt: str | None = None
    name: str | None = None
    favorite: bool | None = None
    source: str | None = None
    aspect: str | None = None
    duration_sec: int | None = None
    resolution: str | None = None
    clips: list[AutomediaClipDto] | None = None
    kind: str | None = None


class AutomediaCampaignUpsert(BaseModel):
    name: str = "Untitled campaign"
    tab: str = "workspace"
    prompt_mode: str = "image"
    filters: dict[str, Any] = Field(default_factory=dict)
    gen_defaults: dict[str, Any] = Field(default_factory=dict)
    assets: list[AutomediaAssetDto] | None = None


class AutomediaCampaignDto(BaseModel):
    id: str
    name: str
    tab: str
    prompt_mode: str
    filters: dict[str, Any] = Field(default_factory=dict)
    gen_defaults: dict[str, Any] = Field(default_factory=dict)
    assets: list[AutomediaAssetDto] = Field(default_factory=list)
    created_at: int | None = None
    updated_at: int | None = None
