from pydantic import BaseModel, Field


class MediaGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    user_id: str | None = None
    # Optional visual reference (image or video) used to guide generation.
    # Prefer reference_base64 for images; large videos can use reference_url instead.
    reference_base64: str | None = None
    reference_mime_type: str | None = Field(None, max_length=100)
    reference_url: str | None = Field(None, max_length=2000)

