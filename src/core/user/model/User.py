from sqlalchemy import JSON, Column, Integer, String, DateTime, ForeignKey, Boolean, Date, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from utilities.dbconfig import Base
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

# At the top of core/user/model/User.py
from core.auth.model.password_reset_token import PasswordResetToken
from core.auth.model.refreshtoken import RefreshToken
from core.notification.model.Notification import Notification
from core.histories.model.history import History

# Add this TYPE_CHECKING block
if TYPE_CHECKING:
    from core.auth.model.password_reset_token import PasswordResetToken
    from core.auth.model.refreshtoken import RefreshToken
    from core.notification.model.Notification import Notification
    from core.histories.model.history import History


class UserStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"

class Gender(str, PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class MembershipType(str, PyEnum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    VIP = "VIP"
    STANDARD = "STANDARD"

class BooleanEnum(str, PyEnum):
    YES = "YES"
    NO = "NO"
    
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, primary_key=True)
    fullname: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String)
    
    # Personal Information
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String, default=None)
    address: Mapped[Optional[str]] = mapped_column(String(300))
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Membership Information
    company: Mapped[Optional[str]] = mapped_column(String, default=None)
    current_branch: Mapped[Optional[str]] = mapped_column(String(100))
    staff_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    
    
    # Professional Information
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    organization_workplace: Mapped[Optional[str]] = mapped_column(String(200))
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    experiences: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Social Media Profiles
    facebook_url: Mapped[Optional[str]] = mapped_column(String(200))
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(20))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(200))
    twitter_url: Mapped[Optional[str]] = mapped_column(String(200))
    instagram_url: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Notification Preferences
    profile_sharing: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    in_app_notification: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    sms_notification: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    status: Mapped[UserStatus] = mapped_column(String, nullable=False, default=UserStatus.ACTIVE)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
    
    
    # Notifications relationship (one-to-many)
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"  # Using dynamic loading for potentially large collections
    )
    
    # Financial Records relationship (one-to-many)
    financial_records: Mapped[List["History"]] = relationship(
        "History",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"  # Using dynamic loading for potentially large collections
    )
    
    # For security/authentication purposes
    @property
    def password(self):
        return self.hashed_password

    @property
    def is_active(self):
        return self.enabled

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)