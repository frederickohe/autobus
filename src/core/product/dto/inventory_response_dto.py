"""Inventory Response DTO"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InventoryResponseDTO(BaseModel):
    """Response model for inventory details."""
    
    # Primary Identifiers
    inventory_id: str
    product_id: str
    location: Optional[str] = None
    name: Optional[str] = None
    
    # Quantities
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int  # Calculated
    quantity_in_transit: int
    quantity_on_order: int
    quantity_backordered: int
    
    # Stock Levels
    min_stock_level: Optional[int] = None
    max_stock_level: Optional[int] = None
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    
    # AI-Optimized Fields
    optimal_stock_level: Optional[int] = None
    stockout_risk_score: Optional[float] = None
    days_of_inventory: Optional[int] = None
    
    # Timestamps
    last_counted_at: Optional[datetime] = None
    last_reordered_at: Optional[datetime] = None
    next_reorder_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "inventory_id": "550e8400-e29b-41d4-a716-446655440001",
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "location": "Warehouse-A",
                "quantity_on_hand": 500,
                "quantity_reserved": 50,
                "quantity_available": 450,
                "quantity_in_transit": 100,
                "quantity_on_order": 200,
                "quantity_backordered": 25,
                "min_stock_level": 100,
                "max_stock_level": 1000,
                "reorder_point": 150,
                "reorder_quantity": 500,
                "optimal_stock_level": 600,
                "stockout_risk_score": 15.5,
                "days_of_inventory": 30,
                "last_counted_at": "2026-03-20T10:30:00Z",
                "last_reordered_at": "2026-03-15T08:00:00Z",
                "next_reorder_date": "2026-03-25T00:00:00Z",
                "created_at": "2026-03-20T10:30:00Z",
                "updated_at": "2026-03-21T08:00:00Z"
            }
        }

    @classmethod
    def from_inventory(cls, inventory):
        """Convert Inventory model to response DTO."""
        return cls(
            inventory_id=str(inventory.inventory_id),
            product_id=str(inventory.product_id),
            location=inventory.location,
            quantity_on_hand=inventory.quantity_on_hand,
            quantity_reserved=inventory.quantity_reserved,
            quantity_available=inventory.quantity_available,
            quantity_in_transit=inventory.quantity_in_transit,
            quantity_on_order=inventory.quantity_on_order,
            quantity_backordered=inventory.quantity_backordered,
            min_stock_level=inventory.min_stock_level,
            max_stock_level=inventory.max_stock_level,
            reorder_point=inventory.reorder_point,
            reorder_quantity=inventory.reorder_quantity,
            optimal_stock_level=inventory.optimal_stock_level,
            stockout_risk_score=inventory.stockout_risk_score,
            days_of_inventory=inventory.days_of_inventory,
            last_counted_at=inventory.last_counted_at,
            last_reordered_at=inventory.last_reordered_at,
            next_reorder_date=inventory.next_reorder_date,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at
        )
