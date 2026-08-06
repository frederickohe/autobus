from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from core.auth.dto.request.password_policy import PASSWORD_MIN_LENGTH


class ResetPassNoAuth(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @model_validator(mode="after")
    def exactly_one_identifier(self):
        email = (self.email or "").strip() if self.email else ""
        phone = (self.phone or "").strip() if self.phone else ""
        if bool(email) == bool(phone):
            raise ValueError("Provide either email or phone, not both or neither")
        self.email = email or None
        self.phone = phone or None
        return self
