"""Order Update DTO"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal


class OrderUpdateDTO(BaseModel):
    """Request model for updating an existing order."""
    
    # Order Details (can be updated)
    order_status: Optional[str] = Field(None, description="Order status: pending, processing, confirmed, cancelled, completed")
    payment_status: Optional[str] = Field(None, description="Payment status: pending, paid, partial, refunded, failed")
    fulfillment_status: Optional[str] = Field(None, description="Fulfillment status: unfulfilled, partial, fulfilled, shipped, delivered")
    
    # Financials (can be updated)
    subtotal_amount: Optional[Decimal] = Field(None, gt=0, description="Subtotal amount before discounts and taxes")
    discount_amount: Optional[Decimal] = Field(None, ge=0, description="Discount amount")
    tax_amount: Optional[Decimal] = Field(None, ge=0, description="Tax amount")
    shipping_amount: Optional[Decimal] = Field(None, ge=0, description="Shipping amount")
    
    # Payment Details (can be updated)
    payment_method: Optional[str] = Field(None, description="Payment method: card, mobile_money, bank_transfer, cash")
    payment_reference: Optional[str] = Field(None, description="Transaction ID from payment provider")
    payment_details: Optional[dict] = Field(None, description="Provider-specific payment data")
    
    # Metadata
    customer_email: Optional[str] = Field(None, description="Customer email address")
    notes: Optional[str] = Field(None, description="Order notes")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    custom_metadata: Optional[dict] = Field(None, description="Flexible storage for additional fields")

    class Config:
        json_schema_extra = {
            "example": {
                "order_status": "confirmed",
                "payment_status": "paid",
                "fulfillment_status": "shipped",
                "subtotal_amount": "150.00",
                "discount_amount": "10.00",
                "notes": "Updated notes",
                "tags": ["vip"],
                "custom_metadata": {"updated_campaign": "summer-sale-2026"}
            }
        }

    @field_validator('subtotal_amount', mode='before')
    @classmethod
    def validate_subtotal(cls, v):
        """Ensure subtotal is positive if provided."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        if v <= 0:
            raise ValueError('subtotal_amount must be greater than 0')
        return v

    @field_validator('discount_amount', 'tax_amount', 'shipping_amount', mode='before')
    @classmethod
    def validate_positive(cls, v):
        """Ensure amounts are non-negative if provided."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v

    def model_dump(self, *args, **kwargs):
        """Override model_dump to exclude None values."""
        d = super().model_dump(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}
