from pydantic import BaseModel, Field


class MediaReferenceItem(BaseModel):
    """Visual ingredient for image/video generation (Flow-style references)."""

    base64: str | None = None
    mime_type: str | None = Field(None, max_length=100)
    url: str | None = Field(None, max_length=2000)


MediaReference = MediaReferenceItem


class MediaGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    user_id: str | None = None
    # Legacy single-reference fields. Prefer `references`.
    reference_base64: str | None = None
    reference_mime_type: str | None = Field(None, max_length=100)
    reference_url: str | None = Field(None, max_length=2000)
    references: list[MediaReferenceItem] | None = None
    aspect_ratio: str | None = Field(
        None,
        description="Output aspect ratio: 16:9, 4:3, 1:1, 3:4, or 9:16.",
    )
    duration_seconds: int | None = Field(
        None,
        ge=1,
        le=16,
        description="Video length in seconds (Veo typically 4, 6, or 8).",
    )
    resolution: str | None = Field(
        None,
        description="Video resolution hint, e.g. 720p or 360p.",
    )
    model: str | None = Field(
        None,
        description="Client model id (Nano Banana / Veo). Server maps known ids.",
    )
    kind: str | None = Field(
        None,
        description="Automedia asset kind: image, video, character, or scene.",
    )

    def resolved_references(self) -> list[MediaReferenceItem]:
        items: list[MediaReferenceItem] = []
        if self.reference_base64 or self.reference_url:
            items.append(
                MediaReferenceItem(
                    base64=self.reference_base64,
                    mime_type=self.reference_mime_type,
                    url=self.reference_url,
                )
            )
        for ref in self.references or []:
            if ref.base64 or ref.url:
                items.append(ref)
        return items
