from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: str
    fullname: str
    email: str
    phone: Optional[str] = None
    
    # Personal Information
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        from_attributes = True  # For ORM compatibility