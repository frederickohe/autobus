from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from utilities.dbconfig import Base

class FileModel(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, unique=True, index=True)
    file_url = Column(String)
    subfolder = Column(String, default="operations/", index=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
