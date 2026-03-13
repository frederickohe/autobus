from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from utilities.dbconfig import Base
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum


class SocialPlatform(str, PyEnum):
    """Supported social media platforms"""
    TWITTER = "TWITTER"
    LINKEDIN = "LINKEDIN"
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    THREADS = "THREADS"
    BLUESKY = "BLUESKY"
    MASTODON = "MASTODON"


class SocialAccount(Base):
    """
    Model for storing connected social media accounts via Blotato integration.
    Each user can connect multiple social media accounts.
    """
    __tablename__ = "social_accounts"

    # Primary Key
    id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, primary_key=True)
    
    # Foreign Key to User
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), nullable=False, index=True)
    
    # Platform Information
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., "TWITTER", "LINKEDIN"
    
    # Blotato Account Information
    account_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # Account ID from Blotato
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Display name from platform
    
    # Platform-specific User ID (if available)
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(100))  # Original platform user ID
    
    # Access Token (encrypted in production)
    access_token: Mapped[Optional[str]] = mapped_column(String(500))  # May not be needed if Blotato manages it
    
    # Refresh Token (if applicable)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Token Expiration
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status and Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Rate limit tracking (posts per minute tracking)
    last_post_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    posts_today: Mapped[int] = mapped_column(nullable=False, default=0)  # Track daily posts
    
    # Connection metadata
    oauth_state: Mapped[Optional[str]] = mapped_column(String(100))  # For validating OAuth callback
    
    def __repr__(self):
        return f"<SocialAccount(id={self.id}, user_id={self.user_id}, platform={self.platform}, account_name={self.account_name})>"
