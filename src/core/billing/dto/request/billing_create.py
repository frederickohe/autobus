from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field

from core.billing.model.billing_charge import BillingSourceType


class BillingCreateRequest(BaseModel):
    customer_email: EmailStr = Field(..., description="Customer email for Paystack checkout")
    amount: Decimal = Field(..., gt=0, description="Bill amount in major currency units (e.g. GHS)")
    currency: str = Field(default="GHS", description="ISO currency code supported by Paystack")
    description: str = Field(..., min_length=1, max_length=500)
    customer_name: Optional[str] = Field(None, max_length=255)
    external_id: Optional[str] = Field(
        None, description="Optional ID from another system (order, subscription, etc.)"
    )
    source_type: BillingSourceType = Field(default=BillingSourceType.CUSTOM)
    callback_url: Optional[str] = Field(
        None, description="Redirect URL after successful payment on Paystack"
    )
    metadata: Optional[dict[str, Any]] = Field(
        None, description="Extra metadata forwarded to Paystack and stored on the charge"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "customer_email": "customer@example.com",
                "customer_name": "Jane Doe",
                "amount": "150.00",
                "currency": "GHS",
                "description": "Premium plan – March 2026",
                "external_id": "ORD-20260318-12345",
                "source_type": "ORDER",
            }
        }
