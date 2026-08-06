from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class OTPVerifyRequest(BaseModel):
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    otp: str = Field(..., min_length=4, max_length=8)
    # When False, OTP is checked but not deleted (e.g. password-reset step before new PIN).
    consume: bool = True