from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from utilities.dbconfig import Base


class WhatsAppAccount(Base):
    """Per-tenant WhatsApp Cloud API connection from Meta Embedded Signup."""

    __tablename__ = "whatsapp_accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, index=True
    )

    waba_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phone_number_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_phone_number: Mapped[Optional[str]] = mapped_column(String(32))
    verified_name: Mapped[Optional[str]] = mapped_column(String(255))
    business_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Encrypted when TOKEN_ENCRYPTION_KEY is configured.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    webhook_subscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
        UniqueConstraint("phone_number_id", name="uq_whatsapp_phone_number_id"),
        UniqueConstraint("user_id", "waba_id", name="uq_whatsapp_user_waba"),
    )
