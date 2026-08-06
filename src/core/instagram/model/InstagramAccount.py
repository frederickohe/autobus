"""Per-tenant Instagram Business account linked via Business Login for Instagram."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from utilities.dbconfig import Base


class InstagramAccount(Base):
    """Instagram professional account connected with Instagram User access tokens."""

    __tablename__ = "instagram_accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, index=True
    )

    # Instagram-scoped user id from Business Login token exchange /me
    ig_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    account_type: Mapped[Optional[str]] = mapped_column(String(64))
    profile_picture_url: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated scopes

    # Encrypted when TOKEN_ENCRYPTION_KEY is configured.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    messaging_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    publishing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
        UniqueConstraint("ig_user_id", name="uq_instagram_ig_user_id"),
        UniqueConstraint("user_id", "ig_user_id", name="uq_instagram_user_ig"),
    )
