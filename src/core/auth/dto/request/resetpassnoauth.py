from pydantic import BaseModel, EmailStr, Field
from core.auth.dto.request.password_policy import PASSWORD_MIN_LENGTH

class ResetPassNoAuth(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
