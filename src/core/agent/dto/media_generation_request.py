from pydantic import BaseModel, Field


class MediaReferenceItem(BaseModel):
    base64: str | None = None
    mime_type: str | None = Field(None, max_length=100)
    url: str | None = Field(None, max_length=2000)


class MediaGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    user_id: str | None = None
    # Legacy single-reference fields. Prefer `references`.
    reference_base64: str | None = None
    reference_mime_type: str | None = Field(None, max_length=100)
    reference_url: str | None = Field(None, max_length=2000)
    references: list[MediaReferenceItem] | None = None
