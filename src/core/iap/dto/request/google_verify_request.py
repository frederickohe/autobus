from typing import Optional

from pydantic import BaseModel, Field


class GooglePlayVerifyRequest(BaseModel):
    """Google Play Billing purchase token from the Android app."""

    purchase_token: str = Field(..., min_length=8)
    product_id: str = Field(..., min_length=3, max_length=255)
    package_name: Optional[str] = Field(None, max_length=255)
    order_id: Optional[str] = Field(None, max_length=255)
