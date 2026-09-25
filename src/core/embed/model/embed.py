"""Per-business embedded chat credentials and idempotent message receipts."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Boolean, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from utilities.dbconfig import Base


class EmbedIntegration(Base):
    __tablename__ = "embed_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    key_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    key_prefix: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    catalog_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="managed", server_default="managed"
    )
    enforce_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    handoff_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class EmbedMessageReceipt(Base):
    __tablename__ = "embed_message_receipts"
    __table_args__ = (
        UniqueConstraint("integration_id", "message_id", name="uq_embed_receipt_message"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("embed_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
