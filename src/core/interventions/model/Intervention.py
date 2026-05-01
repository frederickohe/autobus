from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Date, JSON, Index

from utilities.dbconfig import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Autobus user id (matches users.id in most of this codebase)
    user_id = Column(String, nullable=False, index=True)

    # Links an intervention to a specific daily_conversation batch
    conversation_date = Column(Date, nullable=False, index=True, default=date.today)

    # open | closed
    status = Column(String, nullable=False, default="open", index=True)

    # explicit_user_request | unknown_intent | intent_not_clear | execution_error | external
    trigger = Column(String, nullable=False, default="external")

    # Human-readable description for why intervention was created
    reason = Column(String, nullable=True)

    # Optional metadata (error details, stack trace hash, etc.)
    meta = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)


Index("ix_interventions_user_date", Intervention.user_id, Intervention.conversation_date)
