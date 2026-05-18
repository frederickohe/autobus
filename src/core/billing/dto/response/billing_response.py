from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.billing.model.billing_charge import BillingChargeStatus, BillingSourceType


class BillingResponse(BaseModel):
    id: int
    reference: str
    external_id: Optional[str] = None
    source_type: Optional[BillingSourceType] = None
    customer_email: str
    customer_name: Optional[str] = None
    description: Optional[str] = None
    currency: str
    amount: Decimal
    status: BillingChargeStatus
    payment_url: Optional[str] = Field(
        None, description="Paystack checkout URL for the customer to complete payment"
    )
    access_code: Optional[str] = None
    paystack_status: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    paid_at: Optional[datetime] = None
    created_on: datetime
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_charge(cls, charge) -> "BillingResponse":
        return cls(
            id=charge.id,
            reference=charge.reference,
            external_id=charge.external_id,
            source_type=charge.source_type,
            customer_email=charge.customer_email,
            customer_name=charge.customer_name,
            description=charge.description,
            currency=charge.currency,
            amount=charge.amount,
            status=charge.status,
            payment_url=charge.payment_url,
            access_code=charge.access_code,
            paystack_status=charge.paystack_status,
            metadata=charge.charge_metadata,
            paid_at=charge.paid_at,
            created_on=charge.created_on,
            updated_on=charge.updated_on,
        )
