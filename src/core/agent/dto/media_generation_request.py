from pydantic import BaseModel, Field


class MediaGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    user_id: str | None = None

