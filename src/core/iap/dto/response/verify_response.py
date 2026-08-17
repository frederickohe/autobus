from typing import Optional

from pydantic import BaseModel


class AppleIapVerifyResponse(BaseModel):
    success: bool
    message: str
    subscription_id: Optional[int] = None
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    expires_at: Optional[str] = None
    product_id: Optional[str] = None
    original_transaction_id: Optional[str] = None
    environment: Optional[str] = None
