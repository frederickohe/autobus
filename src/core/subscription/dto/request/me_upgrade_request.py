from pydantic import BaseModel, Field
from typing import Optional


class MeUpgradeRequest(BaseModel):
    """Upgrade the authenticated user's subscription (JWT)."""

    new_plan_id: int = Field(..., gt=0, description="ID of the new subscription plan")
    payment_reference: Optional[str] = Field(
        None, max_length=255, description="Payment transaction reference"
    )
