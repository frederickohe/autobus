import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from utilities.dbconfig import Base


class BillingChargeStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BillingSourceType(str, enum.Enum):
    ORDER = "ORDER"
    SUBSCRIPTION = "SUBSCRIPTION"
    INVOICE = "INVOICE"
    CUSTOM = "CUSTOM"


class BillingCharge(Base):
    """Standalone billing record with Paystack checkout link."""

    __tablename__ = "billing_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    source_type: Mapped[Optional[BillingSourceType]] = mapped_column(Enum(BillingSourceType))
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="GHS")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BillingChargeStatus] = mapped_column(
        Enum(BillingChargeStatus), nullable=False, default=BillingChargeStatus.PENDING
    )
    payment_url: Mapped[Optional[str]] = mapped_column(String(1024))
    access_code: Mapped[Optional[str]] = mapped_column(String(100))
    paystack_status: Mapped[Optional[str]] = mapped_column(String(50))
    gateway_response: Mapped[Optional[str]] = mapped_column(String(255))
    charge_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(20))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<BillingCharge(reference={self.reference}, status={self.status})>"
