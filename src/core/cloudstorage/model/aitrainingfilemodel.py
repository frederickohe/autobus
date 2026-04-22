from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from pgvector.sqlalchemy import Vector
from datetime import datetime
from utilities.dbconfig import Base

class AITrainingFileModel(Base):
    __tablename__ = "ai_training_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    file_name = Column(String, index=True)
    file_url = Column(String)
    subfolder = Column(String, default="ai-training-files/", index=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True, comment="Vector embedding for semantic search")
