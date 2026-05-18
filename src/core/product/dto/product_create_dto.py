"""Product Create DTO"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List


class ProductCreateDTO(BaseModel):
    """Request model for creating a new product."""

    photo: Optional[str] = Field(
        None, min_length=1, max_length=2048, description="Primary product photo URL"
    )
    photos: Optional[List[str]] = Field(
        None, description="One or more product image URLs (2+ supported)"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Product price")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    condition: str = Field(..., min_length=1, max_length=100, description="Product condition")
    number_in_stock: Optional[int] = Field(None, ge=0, description="Current number in stock")
    link: Optional[str] = Field(None, max_length=2048, description="Optional external link")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Wireless Headphones",
                "description": "High-quality wireless headphones with noise cancellation",
                "photos": [
                    "https://cdn.example.com/products/wireless-headphones-1.jpg",
                    "https://cdn.example.com/products/wireless-headphones-2.jpg",
                ],
                "price": 199.99,
                "category": "Electronics",
                "condition": "New",
                "number_in_stock": 10,
                "link": "https://shop.example.com/products/wireless-headphones",
            }
        }

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("photo")
    @classmethod
    def validate_photo(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("photo cannot be empty")
        return v

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, v):
        if v is None:
            return v
        cleaned = [url.strip() for url in v if url and url.strip()]
        if not cleaned:
            raise ValueError("photos must contain at least one non-empty URL")
        return cleaned

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v):
        if not v or not v.strip():
            raise ValueError("condition cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def require_at_least_one_image(self):
        if not self.resolved_photo_urls():
            raise ValueError("At least one image is required via photo or photos")
        return self

    def resolved_photo_urls(self) -> List[str]:
        """Deduplicated image URLs; first entry is treated as primary."""
        urls: List[str] = []
        if self.photos:
            urls.extend(self.photos)
        if self.photo and self.photo not in urls:
            urls.insert(0, self.photo)
        elif self.photo:
            urls = [self.photo] + [u for u in urls if u != self.photo]
        return urls

    @property
    def primary_photo(self) -> str:
        return self.resolved_photo_urls()[0]
