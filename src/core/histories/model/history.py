from sqlalchemy import Column, String, DateTime, Text, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped
import uuid
from datetime import datetime
from typing import Optional
from utilities.dbconfig import Base

class History(Base):
    __tablename__ = "histories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    intent = Column(String, nullable=False)  # e.g., "send_money", "buy_airtime"
    transaction_type = Column(String, nullable=False)  # "debit", "credit"
    amount = Column(Float, nullable=True)
    currency = Column(String, default="GHS")
    recipient = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    data_plan = Column(String, nullable=True)
    category = Column(String, nullable=True)  # For budgets, expenses
    status = Column(String, default="completed")  # "completed", "failed", "pending"
    description = Column(Text, nullable=True)
    transaction_metadata = Column(JSON, nullable=True)  # Additional transaction data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to User
    user = relationship("User", back_populates="financial_records")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "intent": self.intent,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "currency": self.currency,
            "recipient": self.recipient,
            "phone": self.phone,
            "data_plan": self.data_plan,
            "category": self.category,
            "status": self.status,
            "description": self.description,
            "metadata": self.transaction_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }