
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from core.auth.service.sessiondriver import SessionDriver, TokenData
from fastapi_jwt_auth import AuthJWT
from core.exceptions import *
from utilities.dbconfig import SessionLocal
from sqlalchemy.orm import Session
from core.user.model.User import User
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# DTO Models
from core.user.dto.request.user_filter_request import UserFilterRequest
from core.user.dto.response.message_response import MessageResponse
from core.user.dto.response.user_response import UserResponse
from core.user.dto.request.user_update_request import UserUpdateRequest

# Service Class
class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_current_user(self, identifier: str) -> UserResponse:
        # Try to find by email first, then by id as a fallback.
        user = self.db.query(User).filter(User.email == identifier).first()
        if not user:
            user = self.db.query(User).filter(User.id == identifier).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            phone=user.phone,
            
            nationality=user.nationality,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            address=user.address,
            profile_picture_url=user.profile_picture_url,
            
            company=user.company,
            current_branch=user.current_branch,
            staff_id=user.staff_id,
            
            facebook_url=user.facebook_url,
            whatsapp_number=user.whatsapp_number,
            linkedin_url=user.linkedin_url,
            twitter_url=user.twitter_url,
            instagram_url=user.instagram_url,
            
            profile_sharing=user.profile_sharing,
            in_app_notification=user.in_app_notification,
            sms_notification=user.sms_notification,
            enabled=user.enabled,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    def get_user_by_id(self, user_id: str) -> UserResponse:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            phone=user.phone,
            
            nationality=user.nationality,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            address=user.address,
            profile_picture_url=user.profile_picture_url,
            
            company=user.company,
            current_branch=user.current_branch,
            staff_id=user.staff_id,
            
            facebook_url=user.facebook_url,
            whatsapp_number=user.whatsapp_number,
            linkedin_url=user.linkedin_url,
            twitter_url=user.twitter_url,
            instagram_url=user.instagram_url,
            
            profile_sharing=user.profile_sharing,
            in_app_notification=user.in_app_notification,
            sms_notification=user.sms_notification,
            enabled=user.enabled,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    # get user by phone number
    def get_user_by_phone(self, phone: str) -> UserResponse:
        user = self.db.query(User).filter(User.phone == phone).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            phone=user.phone,
            
            nationality=user.nationality,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            address=user.address,
            profile_picture_url=user.profile_picture_url,
            
            company=user.company,
            current_branch=user.current_branch,
            staff_id=user.staff_id,
            
            facebook_url=user.facebook_url,
            whatsapp_number=user.whatsapp_number,
            linkedin_url=user.linkedin_url,
            twitter_url=user.twitter_url,
            instagram_url=user.instagram_url,
            
            profile_sharing=user.profile_sharing,
            in_app_notification=user.in_app_notification,
            sms_notification=user.sms_notification,
            enabled=user.enabled,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    def set_user_enabled_status(self, user_id: str, enabled: bool) -> MessageResponse:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = enabled
        self.db.commit()
        status_msg = "enabled" if enabled else "disabled"
        return MessageResponse(message=f"User {status_msg} successfully")

    def delete_user(self, user_id: str) -> MessageResponse:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        self.db.delete(user)
        self.db.commit()
        return MessageResponse(message="User deleted successfully")

    def get_all_users_paged(self, page: int, size: int):
        query = self.db.query(User)
        total = query.count()
        users = query.offset((page - 1) * size).limit(size).all()
        
        return {
            "total": total,
            "page": page,
            "size": size,
            "users": [
                UserResponse(
                    id=user.id,
                    fullname=user.fullname,
                    email=user.email,
                    phone=user.phone,
                    enabled=user.enabled,
                    status=user.status,
                    created_at=user.created_at,
                    updated_at=user.updated_at  
                ) for user in users
            ]
        }

    def update_user(self, email: str, payload: UserUpdateRequest) -> UserResponse:
            # log the update attempt
            logger.debug(f"Updating user {email} with data: {payload.dict(exclude_unset=True)}")
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            data = payload.dict(exclude_unset=True)
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            return self.get_user_by_id(user.id)

    def update_current_user(self, email: str, payload: UserUpdateRequest) -> UserResponse:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            data = payload.dict(exclude_unset=True)
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            return MessageResponse(message="User updated successfully")