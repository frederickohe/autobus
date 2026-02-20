from sqlalchemy import Column, String, DateTime, JSON, Enum, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from utilities.dbconfig import Base
from typing import TYPE_CHECKING
import enum

if TYPE_CHECKING:
    from core.user.model.User import User

class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"

class NotificationType(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    PROMOTIONAL = "PROMOTIONAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    OTP = "OTP"
    ALERT = "ALERT"

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.UNREAD, index=True)
    
    # SMS specific fields
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_phone: Mapped[str] = mapped_column(String, nullable=True)
    sms_message_id: Mapped[str] = mapped_column(String, nullable=True)
    sms_status: Mapped[str] = mapped_column(String, nullable=True)
    sms_delivery_status: Mapped[str] = mapped_column(String, nullable=True)
    sms_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sms_delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, status={self.status})>"
    # Relationship to user
    user = relationship("User", back_populates="notifications")
    