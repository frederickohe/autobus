from typing import Optional

from pydantic import BaseModel, Field


class AppleIapVerifyRequest(BaseModel):
    """StoreKit 2 signed transaction from the iOS app."""

    signed_transaction: str = Field(..., min_length=20, description="JWS signed transaction")
    plan_id: Optional[int] = Field(None, gt=0, description="Plan the user selected in the app")
    billing_id: Optional[str] = Field(None, max_length=32, description="monthly or annual")
    phone: Optional[str] = Field(None, max_length=32)
