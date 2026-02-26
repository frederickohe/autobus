from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class PaystackInitializeRequest(BaseModel):
    email: EmailStr
    amount: int  # Amount in kobo (smallest currency unit)
    reference: Optional[str] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    channels: Optional[list] = None