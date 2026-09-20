from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from utilities.dbconfig import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AutomediaCampaign(Base):
    """Merchant Automedia studio project (Google Flow-style campaign)."""

    __tablename__ = "automedia_campaigns"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled campaign")
    tab: Mapped[str] = mapped_column(String(32), nullable=False, default="workspace")
    prompt_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="image")
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    gen_defaults: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class AutomediaAsset(Base):
    """Generated or uploaded Automedia asset (image, video, character, scene)."""

    __tablename__ = "automedia_assets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("automedia_campaigns.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    name: Mapped[Optional[str]] = mapped_column(String(255))
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="generated")
    aspect: Mapped[str] = mapped_column(String(16), nullable=False, default="16:9")
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer)
    resolution: Mapped[Optional[str]] = mapped_column(String(16))
    clips: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
