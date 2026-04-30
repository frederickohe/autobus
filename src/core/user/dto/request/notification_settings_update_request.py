from typing import Optional

from pydantic import BaseModel


class NotificationSettingsUpdateRequest(BaseModel):
    in_app_notification: Optional[bool] = None
    sms_notification: Optional[bool] = None

