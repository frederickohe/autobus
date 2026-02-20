from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from core.notification.model.Notification import NotificationType


class SMSNotificationRequest(BaseModel):
    """Request model for sending SMS notification"""
    user_id: str
    phone: str = Field(..., min_length=10, max_length=15, description="Phone number with country code")
    message: str = Field(..., max_length=160, description="SMS message content")
    notification_type: NotificationType = NotificationType.INFO
    data: Optional[Dict[str, Any]] = {}
    send_as_sms: bool = True