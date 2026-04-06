"""Inventory Update DTO"""
from pydantic import BaseModel, Field, validator
from typing import Optional


class InventoryUpdateDTO(BaseModel):
    """Request model for updating inventory."""
    
    # Quantities (can be updated)
    quantity_on_hand: Optional[int] = Field(None, ge=0, description="Quantity currently in stock")
    quantity_reserved: Optional[int] = Field(None, ge=0, description="Quantity reserved for orders")
    quantity_in_transit: Optional[int] = Field(None, ge=0, description="Quantity in transit")
    quantity_on_order: Optional[int] = Field(None, ge=0, description="Quantity on order (not received)")
    quantity_backordered: Optional[int] = Field(None, ge=0, description="Quantity backordered")
    
    # Stock Levels (can be updated)
    min_stock_level: Optional[int] = Field(None, ge=0, description="Minimum safety stock level")
    max_stock_level: Optional[int] = Field(None, ge=0, description="Maximum storage capacity")
    reorder_point: Optional[int] = Field(None, ge=0, description="Level at which to trigger reorder")
    reorder_quantity: Optional[int] = Field(None, ge=0, description="Quantity to order when reordering")
    
    # AI-Optimized Fields (can be updated)
    optimal_stock_level: Optional[int] = Field(None, ge=0, description="AI-calculated optimal stock level")
    stockout_risk_score: Optional[float] = Field(None, ge=0, le=100, description="Stockout probability (0-100)")
    days_of_inventory: Optional[int] = Field(None, ge=0, description="Days of inventory at current rate")
    
    # Location (can be updated)
    location: Optional[str] = Field(None, max_length=100, description="Storage location")
    
    # Name (can be updated)
    name: Optional[str] = Field(None, max_length=255, description="Inventory name")

    class Config:
        json_schema_extra = {
            "example": {
                "quantity_on_hand": 550,
                "quantity_reserved": 60,
                "reorder_point": 100,
                "optimal_stock_level": 650,
                "stockout_risk_score": 12.3,
                "days_of_inventory": 35
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

    def dict(self, *args, **kwargs):
        """Override dict to exclude None values."""
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}
