"""Inventory Create DTO"""
from pydantic import BaseModel, Field, validator
from typing import Optional


class InventoryCreateDTO(BaseModel):
    """Request model for creating inventory."""
    
    # Primary Identifiers
    product_id: str = Field(..., description="UUID of the product")
    location: Optional[str] = Field(None, max_length=100, description="Storage location")
    name: Optional[str] = Field(None, max_length=255, description="Inventory name")
    
    # Quantities
    quantity_on_hand: int = Field(default=0, ge=0, description="Quantity currently in stock")
    quantity_reserved: int = Field(default=0, ge=0, description="Quantity reserved for orders")
    quantity_in_transit: int = Field(default=0, ge=0, description="Quantity in transit")
    quantity_on_order: int = Field(default=0, ge=0, description="Quantity on order (not received)")
    quantity_backordered: int = Field(default=0, ge=0, description="Quantity backordered")
    
    # Stock Levels
    min_stock_level: Optional[int] = Field(None, ge=0, description="Minimum safety stock level")
    max_stock_level: Optional[int] = Field(None, ge=0, description="Maximum storage capacity")
    reorder_point: Optional[int] = Field(None, ge=0, description="Level at which to trigger reorder")
    reorder_quantity: Optional[int] = Field(None, ge=0, description="Quantity to order when reordering")
    
    # AI-Optimized Fields
    optimal_stock_level: Optional[int] = Field(None, ge=0, description="AI-calculated optimal stock level")
    stockout_risk_score: Optional[float] = Field(None, ge=0, le=100, description="Stockout probability (0-100)")
    days_of_inventory: Optional[int] = Field(None, ge=0, description="Days of inventory at current rate")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "location": "Warehouse-A",
                "name": "Main Warehouse Stock",
                "quantity_on_hand": 500,
                "quantity_reserved": 50,
                "quantity_in_transit": 100,
                "quantity_on_order": 200,
                "quantity_backordered": 0,
                "min_stock_level": 100,
                "max_stock_level": 1000,
                "reorder_point": 150,
                "reorder_quantity": 500,
                "optimal_stock_level": 600,
                "stockout_risk_score": 15.5,
                "days_of_inventory": 30
            }
        }

    @validator('min_stock_level', 'max_stock_level', 'reorder_point', 'reorder_quantity', pre=True)
    def validate_stock_levels(cls, v):
        """Validate stock levels are non-negative if provided."""
        if v is None:
            return v
        if v < 0:
            raise ValueError('Stock levels must be non-negative')
        return v

    @validator('stockout_risk_score')
    def validate_risk_score(cls, v):
        """Validate risk score is between 0 and 100."""
        if v is None:
            return v
        if not (0 <= v <= 100):
            raise ValueError('stockout_risk_score must be between 0 and 100')
        return v
