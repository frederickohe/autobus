from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from core.auth.dto.request.password_policy import PASSWORD_MIN_LENGTH


class CreateBusinessRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    fullname: Optional[str] = None
    company: Optional[str] = None

    @model_validator(mode="after")
    def resolve_username(self):
        name = (self.username or self.fullname or "").strip()
        if not name:
            raise ValueError("Username is required")
        self.fullname = name
        self.username = name
        return self


class SwitchBusinessRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class DetachBusinessRequest(BaseModel):
    otp: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
