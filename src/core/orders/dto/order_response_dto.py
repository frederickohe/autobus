"""Order Response DTO"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class OrderResponseDTO(BaseModel):
    """Response model for order details."""
    
    # Primary Identifiers
    order_id: str
    order_number: str
    
    # Customer Relationship
    customer_id: str
    customer_email: Optional[str] = None
    
    # Order Details
    order_type: str
    order_status: str
    payment_status: str
    fulfillment_status: str
    
    # Financials
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    currency_code: str
    
    # Payment Details
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_details: Optional[dict] = None
    
    # Timestamps
    order_date: datetime
    payment_date: Optional[datetime] = None
    fulfillment_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Metadata
    order_source: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_metadata: Optional[dict] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "order_id": "550e8400-e29b-41d4-a716-446655440000",
                "order_number": "ORD-2026-00001",
                "customer_id": "550e8400-e29b-41d4-a716-446655440001",
                "customer_email": "customer@example.com",
                "order_type": "sale",
                "order_status": "confirmed",
                "payment_status": "paid",
                "fulfillment_status": "shipped",
                "subtotal_amount": "150.00",
                "discount_amount": "10.00",
                "tax_amount": "20.00",
                "shipping_amount": "5.00",
                "total_amount": "165.00",
                "currency_code": "GHS",
                "payment_method": "card",
                "payment_reference": "TXN-12345",
                "payment_details": {"provider": "paystack", "reference": "TXN-12345"},
                "order_date": "2026-03-20T10:30:00Z",
                "payment_date": "2026-03-20T10:35:00Z",
                "fulfillment_date": "2026-03-21T08:00:00Z",
                "delivery_date": None,
                "created_at": "2026-03-20T10:30:00Z",
                "updated_at": "2026-03-21T08:00:00Z",
                "order_source": "web",
                "notes": "Handle with care",
                "tags": ["urgent", "vip"],
                "custom_metadata": {"campaign_id": "spring-sale-2026"}
            }
        }

    @classmethod
    def from_order(cls, order):
        """Convert Order model to response DTO."""
        return cls(
            order_id=str(order.order_id),
            order_number=order.order_number,
            customer_id=str(order.customer_id),
            customer_email=order.customer_email,
            order_type=order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
            order_status=order.order_status.value if hasattr(order.order_status, 'value') else order.order_status,
            payment_status=order.payment_status.value if hasattr(order.payment_status, 'value') else order.payment_status,
            fulfillment_status=order.fulfillment_status.value if hasattr(order.fulfillment_status, 'value') else order.fulfillment_status,
            subtotal_amount=order.subtotal_amount,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            shipping_amount=order.shipping_amount,
            total_amount=order.total_amount,
            currency_code=order.currency_code,
            payment_method=order.payment_method.value if order.payment_method and hasattr(order.payment_method, 'value') else order.payment_method,
            payment_reference=order.payment_reference,
            payment_details=order.payment_details,
            order_date=order.order_date,
            payment_date=order.payment_date,
            fulfillment_date=order.fulfillment_date,
            delivery_date=order.delivery_date,
            created_at=order.created_at,
            updated_at=order.updated_at,
            order_source=order.order_source.value if order.order_source and hasattr(order.order_source, 'value') else order.order_source,
            notes=order.notes,
            tags=order.tags,
            custom_metadata=order.custom_metadata
        )
