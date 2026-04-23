"""Product Update DTO"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ProductUpdateDTO(BaseModel):
    """Request model for updating an existing product."""
    
    # Product Details (can be updated)
    photo: Optional[str] = Field(None, min_length=1, max_length=2048, description="Product photo URL")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: Optional[float] = Field(None, ge=0, description="Product price")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    condition: Optional[str] = Field(None, min_length=1, max_length=100, description="Product condition")
    number_in_stock: Optional[int] = Field(None, ge=0, description="Current number in stock")
    link: Optional[str] = Field(None, max_length=2048, description="Optional external link")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Wireless Headphones Pro",
                "photo": "https://cdn.example.com/products/wireless-headphones-pro.jpg",
                "price": 229.99,
                "category": "Electronics",
                "condition": "Like New",
                "number_in_stock": 8,
                "link": "https://shop.example.com/products/wireless-headphones-pro"
            }
        }

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate product name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('name cannot be empty')
            return v.strip()
        return v

    @field_validator('photo')
    @classmethod
    def validate_photo(cls, v):
        """Validate photo URL if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('photo cannot be empty')
        return v

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        """Validate condition if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('condition cannot be empty')
        return v

    def model_dump(self, *args, **kwargs):
        """Override model_dump to exclude None values."""
        d = super().model_dump(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}
