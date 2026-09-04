"""Product image response DTO"""
from pydantic import BaseModel
from datetime import datetime

from core.cloudstorage.service.storageservice import refresh_public_object_url
from core.product.media import media_looks_like_video


class ProductImageResponseDTO(BaseModel):
    image_id: str
    product_id: str
    url: str
    sort_order: int
    is_primary: bool
    media_type: str = "image"
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_image(cls, image) -> "ProductImageResponseDTO":
        return cls(
            image_id=str(image.image_id),
            product_id=str(image.product_id),
            url=refresh_public_object_url(image.url),
            sort_order=image.sort_order,
            is_primary=image.is_primary,
            media_type="video" if media_looks_like_video(image.url) else "image",
            created_at=image.created_at,
        )
