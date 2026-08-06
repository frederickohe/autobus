from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class VerifyAccountRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)

    @model_validator(mode="after")
    def exactly_one_identifier(self):
        email = (self.email or "").strip() if self.email else ""
        phone = (self.phone or "").strip() if self.phone else ""
        if bool(email) == bool(phone):
            raise ValueError("Provide either email or phone, not both or neither")
        self.email = email or None
        self.phone = phone or None
        return self
