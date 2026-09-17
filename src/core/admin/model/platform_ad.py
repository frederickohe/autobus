from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from utilities.dbconfig import Base


class PlatformAd(Base):
    __tablename__ = "platform_ads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="image")
    media_url: Mapped[str] = mapped_column(Text, nullable=False)
    link_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
