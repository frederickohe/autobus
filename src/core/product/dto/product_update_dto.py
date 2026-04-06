"""Product Update DTO"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List


class ProductUpdateDTO(BaseModel):
    """Request model for updating an existing product."""
    
    # Product Description (can be updated)
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    
    # Identifiers (can be updated)
    barcode: Optional[str] = Field(None, max_length=100, description="UPC/EAN barcode")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    attributes: Optional[dict] = Field(None, description="Product-specific attributes (flexible JSON)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Wireless Headphones Pro",
                "category": "Electronics",
                "brand": "AudioPro",
                "tags": ["audio", "wireless", "premium", "professional"],
                "attributes": {
                    "color": "Silver",
                    "battery_life": "40 hours",
                    "weight": "240g"
                }
            }
        }

    @validator('name')
    def validate_name(cls, v):
        """Validate product name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('name cannot be empty')
            return v.strip()
        return v

    @validator('barcode')
    def validate_barcode(cls, v):
        """Validate barcode if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    def dict(self, *args, **kwargs):
        """Override dict to exclude None values."""
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}
