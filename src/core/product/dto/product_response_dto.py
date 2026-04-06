"""Product Response DTO"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductResponseDTO(BaseModel):
    """Response model for product details."""
    
    # Primary Identifiers
    product_id: str
    inventory_id: str
    barcode: Optional[str] = None
    
    # Product Description
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    
    # Metadata
    tags: Optional[List[str]] = None
    attributes: Optional[dict] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_sold_at: Optional[datetime] = None
    last_ordered_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "inventory_id": "PROD-WIRELESS-HEADPHONES-001",
                "barcode": "978-0-596-00712-6",
                "name": "Premium Wireless Headphones",
                "description": "High-quality wireless headphones with noise cancellation",
                "category": "Electronics",
                "brand": "AudioPro",
                "tags": ["audio", "wireless", "premium"],
                "attributes": {
                    "color": "Black",
                    "battery_life": "30 hours",
                    "weight": "250g"
                },
                "created_at": "2026-03-20T10:30:00Z",
                "updated_at": "2026-03-21T08:00:00Z",
                "last_sold_at": "2026-03-21T07:30:00Z",
                "last_ordered_at": "2026-03-21T06:00:00Z"
            }
        }

    @classmethod
    def from_product(cls, product):
        """Convert Product model to response DTO."""
        return cls(
            product_id=str(product.product_id),
            inventory_id=product.inventory_id,
            barcode=product.barcode,
            name=product.name,
            description=product.description,
            category=product.category,
            brand=product.brand,
            tags=product.tags,
            attributes=product.attributes,
            created_at=product.created_at,
            updated_at=product.updated_at,
            last_sold_at=product.last_sold_at,
            last_ordered_at=product.last_ordered_at
        )
