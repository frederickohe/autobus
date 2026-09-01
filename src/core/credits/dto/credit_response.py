from typing import Dict, List, Optional

from pydantic import BaseModel


class CreditBalanceItem(BaseModel):
    credit_type: str
    label: str
    allocated: float
    remaining: float
    used: float
    wallet_cost: float = 0
    period_start: str
    period_end: str


class WalletBalance(BaseModel):
    remaining: float
    allocated: float
    used: float


class CreditPackItem(BaseModel):
    id: str
    name: str
    credits: float
    price_usd: float
    paystack_amount: float
    apple_product_id: str
    google_play_product_id: str = ""
    description: str
    details: str = ""


class UserCreditsResponse(BaseModel):
    user_id: str
    plan_id: Optional[int] = None
    plan_name: str
    has_active_subscription: bool
    wallet: Optional[WalletBalance] = None
    costs: Dict[str, float] = {}
    packs: List[CreditPackItem] = []
    credits: Dict[str, CreditBalanceItem]


class CreditCheckoutRequest(BaseModel):
    pack_id: str
    email: Optional[str] = None
    callback_url: Optional[str] = None
