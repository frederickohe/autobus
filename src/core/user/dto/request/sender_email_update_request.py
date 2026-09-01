from pydantic import BaseModel, field_validator


class SenderEmailUpdateRequest(BaseModel):
    sender_email: str

    @field_validator("sender_email", mode="before")
    @classmethod
    def require_text(cls, value):
        text = str(value or "").strip()
        if not text:
            raise ValueError("Enter a from email")
        return text
