from typing import Optional

from pydantic import BaseModel, Field, model_validator


class UserLoginRequest(BaseModel):
    email: Optional[str] = Field(default=None, min_length=1, max_length=255)
    username: Optional[str] = Field(default=None, min_length=1, max_length=255)
    # Login verifies credentials; do not apply create/reset password policy here.
    password: str = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_email_or_username(self):
        if not self.email and not self.username:
            raise ValueError("Email or username is required")
        return self

    @property
    def login_identifier(self) -> str:
        return (self.email or self.username or "").strip()
