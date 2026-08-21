from pydantic import BaseModel, Field
from typing import List


class SentSmsItem(BaseModel):
    """One outbound SMS recorded when customer messaging send succeeds."""

    phone: str = Field(..., description="Recipient phone number")
    message: str = Field(..., description="SMS body")
    sent_at: str = Field(..., description="ISO 8601 timestamp (UTC)")
    status: str = Field(default="Sent", description="Delivery status label")


class SentSmsResponse(BaseModel):
    messages: List[SentSmsItem]
    total_returned: int
