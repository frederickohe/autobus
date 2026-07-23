from pydantic import BaseModel, EmailStr


class VerifyAccountRequest(BaseModel):
    email: EmailStr
