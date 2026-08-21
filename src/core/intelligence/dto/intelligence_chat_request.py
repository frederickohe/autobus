from pydantic import BaseModel, Field


class IntelligenceChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
