"""Per-tenant GreenMall store linked with a first-party API key."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from utilities.dbconfig import Base


class GreenMallAccount(Base):
    """GreenMall online store / POS connection for an Autobus business."""

    __tablename__ = "greenmall_accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, index=True
    )

    store_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    store_name: Mapped[Optional[str]] = mapped_column(String(255))
    store_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Encrypted when TOKEN_ENCRYPTION_KEY is configured.
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("store_id", name="uq_greenmall_store_id"),
        UniqueConstraint("user_id", "store_id", name="uq_greenmall_user_store"),
    )
