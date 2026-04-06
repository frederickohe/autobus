"""Product Create DTO"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List


class ProductCreateDTO(BaseModel):
    """Request model for creating a new product."""
    
    # Product Description
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    
    # Optional Identifiers
    barcode: Optional[str] = Field(None, max_length=100, description="UPC/EAN barcode")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    attributes: Optional[dict] = Field(None, description="Product-specific attributes (flexible JSON)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Wireless Headphones",
                "description": "High-quality wireless headphones with noise cancellation",
                "category": "Electronics",
                "brand": "AudioPro",
                "barcode": "978-0-596-00712-6",
                "tags": ["audio", "wireless", "premium"],
                "attributes": {
                    "color": "Black",
                    "battery_life": "30 hours",
                    "weight": "250g"
                }
            }
        }

    @validator('name')
    def validate_name(cls, v):
        """Validate product name."""
        if not v or not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()

    @validator('barcode')
    def validate_barcode(cls, v):
        """Validate barcode format."""
        if v:
            v = v.strip()
            if not v:
                return None
        return v
