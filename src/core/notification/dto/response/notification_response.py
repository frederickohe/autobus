from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from core.notification.model.Notification import NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    data: Dict[str, Any]
    status: NotificationStatus
    created_at: datetime
    read_at: Optional[datetime] = None
    updated_at: datetime
    
    # SMS fields
    sms_sent: bool
    sms_phone: Optional[str] = None
    sms_message_id: Optional[str] = None
    sms_status: Optional[str] = None
    sms_delivery_status: Optional[str] = None
    sms_sent_at: Optional[datetime] = None
    sms_delivered_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

    @classmethod
    def from_orm(cls, notification):
        """Convert ORM model to Pydantic model"""
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type,
            data=notification.data,
            status=notification.status,
            created_at=notification.created_at,
            read_at=notification.read_at,
            updated_at=notification.updated_at,
            sms_sent=notification.sms_sent,
            sms_phone=notification.sms_phone,
            sms_message_id=notification.sms_message_id,
            sms_status=notification.sms_status,
            sms_delivery_status=notification.sms_delivery_status,
            sms_sent_at=notification.sms_sent_at,
            sms_delivered_at=notification.sms_delivered_at
        )