from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from utilities.dbconfig import Base
from typing import TYPE_CHECKING
from sqlalchemy.orm import mapped_column, relationship, Mapped

if TYPE_CHECKING:
    from core.user.model.User import User
    
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(20), primary_key=True, unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey('users.id'), nullable=False)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    access_code = Column(String(100), nullable=True)
    amount = Column(Integer, nullable=False)  # in kobo
    email = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, success, failed
    gateway_response = Column(String(200), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    transaction_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to user
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(reference={self.reference}, status={self.status})>"