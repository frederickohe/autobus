from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from utilities.dbconfig import Base


class CreditPurchase(Base):
    """Idempotent ledger for IAP and Paystack credit pack grants."""

    __tablename__ = "credit_purchases"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "transaction_id",
            name="uq_credit_purchase_provider_txn",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(20), nullable=False)
    pack_id: Mapped[str] = mapped_column(String(32), nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
