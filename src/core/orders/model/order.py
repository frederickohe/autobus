import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, String, Integer,
    DECIMAL, JSON, ARRAY, Text, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from utilities.dbconfig import Base


class OrderType(str, Enum):
    """Order type enumeration"""
    SALE = "sale"
    REFUND = "refund"
    EXCHANGE = "exchange"
    WHOLESALE = "wholesale"
    DROPSHIP = "dropship"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OrderPaymentStatus(str, Enum):
    """Order payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    FAILED = "failed"


class FulfillmentStatus(str, Enum):
    """Fulfillment status enumeration"""
    UNFULFILLED = "unfulfilled"
    PARTIAL = "partial"
    FULFILLED = "fulfilled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class OrderPaymentMethod(str, Enum):
    """Order payment method enumeration"""
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class OrderSource(str, Enum):
    """Order source enumeration"""
    CHAT = "chat"
    WEB = "web"
    PHONE = "phone"
    IN_PERSON = "in-person"


class Order(Base):
    """
    Order model for managing customer orders.
    Tracks order details, payment, and fulfillment information.
    """
    __tablename__ = "orders"

    # Primary Identifiers
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Customer Relationship
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(150))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(30))
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    customer_location: Mapped[Optional[str]] = mapped_column(String(255))

    # Order Details
    order_type: Mapped[str] = mapped_column(SQLEnum(OrderType), nullable=False)
    order_items: Mapped[Optional[list]] = mapped_column(JSON)
    order_status: Mapped[str] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_status: Mapped[str] = mapped_column(SQLEnum(OrderPaymentStatus), default=OrderPaymentStatus.PENDING, nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(SQLEnum(FulfillmentStatus), default=FulfillmentStatus.UNFULFILLED, nullable=False)

    # Financials
    total_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    subtotal_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    shipping_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="GHS", nullable=False)

    # Payment Details
    payment_method: Mapped[Optional[str]] = mapped_column(SQLEnum(OrderPaymentMethod))
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255))
    payment_details: Mapped[Optional[dict]] = mapped_column(JSON)

    # Timestamps
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fulfillment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    order_source: Mapped[Optional[str]] = mapped_column(SQLEnum(OrderSource))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    custom_metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self):
        return f"<Order(order_id={self.order_id}, order_number={self.order_number}, customer_name={self.customer_name}, total_amount={self.total_amount})>"
