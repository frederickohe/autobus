"""Order Create DTO"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal, InvalidOperation


class OrderCreateDTO(BaseModel):
    """Request model for creating a new order."""

    @staticmethod
    def _to_decimal(v, field_name: str) -> Decimal:
        """Convert supported numeric inputs into Decimal."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float, str)):
            try:
                return Decimal(str(v))
            except (InvalidOperation, ValueError):
                raise ValueError(f'{field_name} must be a valid number')
        raise ValueError(f'{field_name} must be a valid number')

    # Customer Relationship
    customer_name: str = Field(..., min_length=1, max_length=150, description="Customer full name")
    customer_phone: str = Field(..., min_length=1, max_length=30, description="Customer phone number")
    customer_email: Optional[str] = Field(None, description="Customer email address")
    customer_location: Optional[str] = Field(None, max_length=255, description="Customer location or address")
    
    # Order Details
    order_type: str = Field(..., description="Order type: sale, refund, exchange, wholesale, dropship")
    item_name: str = Field(..., min_length=1, max_length=255, description="Name of item ordered")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    order_source: Optional[str] = Field(None, description="Order source: chat, web, phone, in-person")
    
    # Financials
    subtotal_amount: Optional[Decimal] = Field(
        default=Decimal("0"),
        ge=0,
        description="Subtotal amount before discounts and taxes"
    )
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Discount amount")
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Tax amount")
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Shipping amount")
    currency_code: str = Field(default="GHS", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    
    # Payment Details
    payment_method: Optional[str] = Field(None, description="Payment method: card, mobile_money, bank_transfer, cash")
    payment_reference: Optional[str] = Field(None, description="Transaction ID from payment provider")
    payment_details: Optional[dict] = Field(None, description="Provider-specific payment data")
    
    # Metadata
    notes: Optional[str] = Field(None, description="Order notes")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    custom_metadata: Optional[dict] = Field(None, description="Flexible storage for additional fields")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "Jane Doe",
                "customer_phone": "+233201234567",
                "customer_email": "customer@example.com",
                "customer_location": "Accra, Ghana",
                "order_type": "sale",
                "item_name": "Rice Bag 5kg",
                "quantity": 2,
                "order_source": "web",
                "subtotal_amount": "150.00",
                "discount_amount": "10.00",
                "tax_amount": "20.00",
                "shipping_amount": "5.00",
                "currency_code": "GHS",
                "payment_method": "card",
                "payment_reference": "TXN-12345",
                "payment_details": {"provider": "paystack", "reference": "TXN-12345"},
                "notes": "Handle with care",
                "tags": ["urgent", "vip"],
                "custom_metadata": {"campaign_id": "spring-sale-2026"}
            }
        }

    @field_validator('subtotal_amount', mode='before')
    @classmethod
    def validate_subtotal(cls, v):
        """Ensure subtotal is non-negative."""
        if v is None:
            return Decimal("0")
        v = cls._to_decimal(v, 'subtotal_amount')
        if v < 0:
            raise ValueError('subtotal_amount must be non-negative')
        return v

    @field_validator('discount_amount', 'tax_amount', 'shipping_amount', mode='before')
    @classmethod
    def validate_positive(cls, v):
        """Ensure amounts are non-negative."""
        if v is None:
            return Decimal("0")
        v = cls._to_decimal(v, 'Amount')
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v
