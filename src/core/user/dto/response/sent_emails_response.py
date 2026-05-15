from pydantic import BaseModel, Field
from typing import List


class SentEmailItem(BaseModel):
    """One outbound message recorded when EmailTool send succeeds."""

    to: str = Field(..., description="Recipient address")
    subject: str = Field(..., description="Subject line")
    sent_at: str = Field(..., description="ISO 8601 timestamp (UTC)")


class SentEmailsResponse(BaseModel):
    emails: List[SentEmailItem]
    total_returned: int
