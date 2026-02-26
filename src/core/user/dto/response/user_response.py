from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional, List


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
    profile_picture_url: Optional[str] = None
    
    # Membership Information
    company: Optional[str] = None
    current_branch: Optional[str] = None
    staff_id: Optional[str] = None
    
    # Social Media Profiles
    facebook_url: Optional[str] = None
    whatsapp_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    instagram_url: Optional[str] = None
    
    # Notification Preferences
    profile_sharing: Optional[str] = None
    in_app_notification: Optional[str] = None
    sms_notification: Optional[str] = None
    
    # Status and Timestamps
    status: str
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True