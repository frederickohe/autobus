from typing import List

from pydantic import BaseModel

from core.billing.dto.response.billing_response import BillingResponse


class BillingPaginatedResponse(BaseModel):
    items: List[BillingResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool
