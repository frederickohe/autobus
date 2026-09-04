from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LinkedBusinessItem(BaseModel):
    id: str
    email: str
    fullname: str
    company: Optional[str] = None
    is_manager: bool = False
    is_active: bool = False
    onboarding_completed: bool = True
    managed_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LinkedBusinessListResponse(BaseModel):
    manager_id: str
    active_user_id: str
    items: List[LinkedBusinessItem]
