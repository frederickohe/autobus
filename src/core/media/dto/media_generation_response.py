from pydantic import BaseModel, Field


class ImageGenerationResponse(BaseModel):
    prompt: str
    image_base64: str = Field(..., description="Base64-encoded image bytes from Google (Nana Banana / Gemini image model)")
    mime_type: str = "image/png"
    image_url: str | None = Field(
        None,
        description="Stored public URL when the generated image was uploaded to storage.",
    )
    aspect_ratio: str | None = None
    kind: str | None = None


class VideoGenerationResponse(BaseModel):
    prompt: str
    video_url: str = Field(..., description="Direct URL from Google Veo (Generative Language API)")
    stored_url: str | None = Field(
        None,
        description="Contabo URL when store=true; omitted when returning Google URL only",
    )
    aspect_ratio: str | None = None
    duration_seconds: int | None = None
    resolution: str | None = None
    kind: str | None = None
