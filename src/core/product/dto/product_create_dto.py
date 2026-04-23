"""Product Create DTO"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ProductCreateDTO(BaseModel):
    """Request model for creating a new product."""
    
    # Product Details
    photo: str = Field(..., min_length=1, max_length=2048, description="Product photo URL")
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
                "photo": "https://cdn.example.com/products/wireless-headphones.jpg",
                "price": 199.99,
                "category": "Electronics",
                "condition": "New",
                "number_in_stock": 10,
                "link": "https://shop.example.com/products/wireless-headphones"
            }
        }

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate product name."""
        if not v or not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()

    @field_validator('photo')
    @classmethod
    def validate_photo(cls, v):
        """Validate photo URL is not blank."""
        if not v or not v.strip():
            raise ValueError('photo cannot be empty')
        return v.strip()

    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        """Validate condition is not blank."""
        if not v or not v.strip():
            raise ValueError('condition cannot be empty')
        return v.strip()
