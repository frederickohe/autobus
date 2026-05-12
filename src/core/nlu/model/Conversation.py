
from sqlalchemy import JSON, Column, Integer, String, DateTime, Date
from utilities.dbconfig import Base
from datetime import datetime

class DailyConversation(Base):
    """Persisted conversation sessions (multiple per user per day allowed)."""
    __tablename__ = "daily_conversations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    conversation_date = Column(Date, nullable=False, index=True)
    conversation_state = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = ()
