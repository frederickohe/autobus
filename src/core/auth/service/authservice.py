from fastapi.responses import JSONResponse
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi import HTTPException
from fastapi import status
from datetime import datetime, timedelta, timezone
from core.auth.service.sessiondriver import SessionDriver
from core.exceptions.AuthException import InvalidCredentialsError
from core.exceptions.UserException import UserAlreadyExistsError
from core.user.model.User import User
from core.otp.service.otpservice import OTPService
import secrets
import string
import logging
import os
import uuid

from core.chatwoot.model.ChatwootAccount import ChatwootAccount
from core.chatwoot.service.chatwoot_api_service import (
    ChatwootClient,
    chatwoot_enabled,
    derive_chatwoot_password,
)
from utilities.crypto import encrypt_secret

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.session_driver = SessionDriver()
        self.otp_service = OTPService(db)

    def hash_password(self, password: str) -> str:
        """Hash a plain-text password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against a hashed one."""
        return pwd_context.verify(plain_password, hashed_password)

    def generate_user_id(self):
        """Generate a random user ID with alphanumeric characters."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for i in range(20))

    def create_user(self, request: BaseModel):
        """Create a new user in the database."""
        existing_user = (
            self.db.query(User)
            .filter(
                (User.email == request.email) | (User.fullname == request.fullname)
            )
            .first()
        )

        if existing_user:
            if existing_user.email == request.email:
                raise UserAlreadyExistsError(field="email")
            else:
                raise UserAlreadyExistsError(field="fullname")
            
        user_id = self.generate_user_id()

        db_user = User(
            id=user_id,
            fullname=request.fullname,
            phone=request.phone,
            email=request.email,
            hashed_password=self.hash_password(request.password),
            profile_picture_url=request.profile_picture_url,
            
            nationality=request.nationality,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            address=request.address,
            
            company=request.company,
            current_branch=request.current_branch,
            staff_id=request.staff_id,
            
            facebook_url=request.facebook_url,
            whatsapp_number=request.whatsapp_number,
            linkedin_url=request.linkedin_url,
            twitter_url=request.twitter_url,
            instagram_url=request.instagram_url,
            
            in_app_notification=request.in_app_notification,
            sms_notification=request.sms_notification,
            
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        otp_send_result = None
        try:
            # Prefer phone OTP for account enablement (current `/verify-otp` contract uses phone).
            if getattr(request, "phone", None):
                otp_send_result = self.otp_service.send_otp_phone(request.phone)
            elif getattr(request, "email", None):
                otp_send_result = self.otp_service.send_otp_email(request.email)
        except Exception as e:
            logger.error(f"OTP send error during signup for user {db_user.id}: {e}", exc_info=True)

        # Optional: Provision a matching tenant in Chatwoot (self-hosted)
        # Controlled via env vars:
        # - CHATWOOT_BASE_URL (e.g. http://host.docker.internal:3000)
        # - CHATWOOT_PLATFORM_API_TOKEN (from Chatwoot super admin platform app)
        try:
            if chatwoot_enabled():
                base_url = os.getenv("CHATWOOT_BASE_URL", "").strip()
                token = os.getenv("CHATWOOT_PLATFORM_API_TOKEN", "").strip()
                if base_url and token:
                    account_name = (
                        getattr(request, "company", None)
                        or getattr(request, "fullname", None)
                        or "Autobus Client"
                    ).strip()
                    chatwoot_password = derive_chatwoot_password(
                        user_id=db_user.id,
                        email=request.email,
                        autobus_password_hash=db_user.hashed_password,
                    )
                    client = ChatwootClient(base_url=base_url, platform_api_token=token)

                    import asyncio

                    cw_account_id, cw_user_id, cw_access_token = asyncio.run(
                        client.provision_account_and_user(
                            account_name=account_name,
                            email=request.email,
                            name=request.fullname,
                            password=chatwoot_password,
                            support_email=request.email,
                        )
                    )

                    mapping = ChatwootAccount(
                        id=f"cw_{str(uuid.uuid4())[:12]}",
                        user_id=db_user.id,
                        chatwoot_account_id=int(cw_account_id),
                        chatwoot_user_id=int(cw_user_id),
                        chatwoot_user_access_token_encrypted=encrypt_secret(cw_access_token)
                        or cw_access_token,
                    )
                    self.db.add(mapping)
                    self.db.commit()
        except Exception as e:
            # Do not block signup if Chatwoot is down/misconfigured.
            logger.warning(f"[CHATWOOT] Provisioning skipped/failed for user {db_user.id}: {e}")
        
        otp_sent = bool(getattr(otp_send_result, "success", False)) if otp_send_result is not None else False
        otp_message = (
            "User account created successfully. Please verify your phone number with the OTP sent to you."
            if otp_sent
            else "User account created successfully, but we couldn't send your OTP. Please request a new OTP."
        )

        return {
            "message": otp_message,
            "user_id": db_user.id,
            "verification_required": True,
            "otp_sent": otp_sent,
            "otp_send_error": None if otp_sent else getattr(otp_send_result, "message", None),
        }
    
    def verify_and_enable_user(self, phone: str, otp: str):
        """Verify OTP and enable user account"""
        # Validate OTP
        is_valid = self.otp_service.validate_otp(phone=phone, otp=otp)
        
        if not is_valid:
            return {
                "success": False,
                "message": "Invalid or expired OTP"
            }
        
        # Find user by phone
        user = self.db.query(User).filter(User.phone == phone).first()
        
        if not user:
            return {
                "success": False,
                "message": "User not found"
            }
        
        # Enable user account
        user.enabled = True
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

        return {
            "success": True,
            "message": "Phone number verified successfully. Your account is now active.",
            "user_id": user.id
        }
           
    def authenticate_user(self, email: str, password: str):
        db_user = self.db.query(User).filter(User.email == email).first()

        if not db_user:
            raise InvalidCredentialsError()

        if not self.verify_password(password, db_user.hashed_password):
            raise InvalidCredentialsError()

        return db_user

    def signin(self, user: BaseModel):
        """Login the user by generating a JWT token and returning tokens."""
        db_user = self.authenticate_user(user.email, user.password)

        access_token = self.session_driver.create_access_token(
            data={"sub": db_user.email},
            expires_delta=timedelta(minutes=self.session_driver.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        refresh_token = self.session_driver.create_refresh_token(
            data={"sub": db_user.email}
        )

        self.session_driver.store_tokens(access_token, refresh_token)

        return JSONResponse(
            status_code=200,
            content={
                "status": "Login successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.session_driver.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            },
        )

    def signout(self, token: str):
        try:
            # Decode without expiration check
            payload = jwt.decode(
                token, 
                self.session_driver.SECRET_KEY, 
                algorithms=[self.session_driver.ALGORITHM],
                options={"verify_exp": False}
            )
            email = payload.get("sub")
            
            if not email:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Triple protection:
            # 1. Blacklist this specific token
            self.session_driver.blacklist_token(token)
            
            # 2. Remove token storage
            self.session_driver.remove_tokens(email)
            
            return JSONResponse(
                status_code=200,
                content={"message": "Logout successful"}
            )
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            # Still attempt to blacklist
            self.session_driver.blacklist_token(token)
            raise HTTPException(status_code=500, detail="Logout processing error")

    def refresh_tokens(self, refresh_token: str):
        """Refresh access token using refresh token"""
        try:
            new_access_token = self.session_driver.refresh_access_token(refresh_token)
            
            return JSONResponse(
                status_code=200,
                content={
                    "access_token": new_access_token,
                    "token_type": "bearer",
                    "expires_in": self.session_driver.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                }
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        
    def signout_all(self, token: str):
        """Logout the user from all devices by invalidating all their tokens"""
        try:
            payload = jwt.decode(
                token, 
                self.session_driver.SECRET_KEY, 
                algorithms=[self.session_driver.ALGORITHM],
                options={"verify_exp": False}
            )
            email = payload.get("sub")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Triple protection:
            # 1. Blacklist this specific token
            self.session_driver.blacklist_token(token)
            
            # 2. Remove token storage
            self.session_driver.remove_tokens(email)
            
            return JSONResponse(
                status_code=200,
                content={"message": "Logged out from all devices"}
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_account(self, email: str):
        """Verify user account using email or username"""
        try:
            db_user = self.db.query(User).filter(User.email == email).first()

            if not db_user:
                raise InvalidCredentialsError()
            
            return JSONResponse(
                status_code=200,
                content={"message": "Account verified successfully"}
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not valid or expired"
            )
            
    def reset_password(self, request: BaseModel):
        """Reset password using a valid reset token (authenticated version)"""
        try:
            # Verify the reset token
            payload = jwt.decode(
                request.reset_token,
                self.session_driver.SECRET_KEY,
                algorithms=[self.session_driver.ALGORITHM]
            )
            
            if payload.get("type") != "reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type"
                )
                
            email = payload.get("sub")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token payload"
                )
            
            # Find user and update password
            db_user = self.db.query(User).filter(User.email == email).first()
            if not db_user:
                raise InvalidCredentialsError()
                
            db_user.hashed_password = self.hash_password(request.new_password)
            self.db.commit()
            
            # Invalidate all existing tokens
            self.session_driver.remove_tokens(email)
            
            return JSONResponse(
                status_code=200,
                content={"message": "Password reset successfully"}
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

    def reset_password_no_auth(self, request: BaseModel):
        """Reset password without authentication (for forgotten password flow)"""
        try:
            # Find user by email
            db_user = self.db.query(User).filter(User.email == request.email).first()
            if not db_user:
                # Don't reveal whether email exists for security
                return JSONResponse(
                    status_code=200,
                    content={"message": "If the email exists, password has been reset"}
                )
                
            # Update password
            db_user.hashed_password = self.hash_password(request.new_password)
            self.db.commit()
            
            # Invalidate all existing tokens
            self.session_driver.remove_tokens(request.email)
            
            return JSONResponse(
                status_code=200,
                content={"message": "If the email exists, password has been reset"}
            )
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error resetting password"
            )

    def generate_password_reset_token(self, email: str) -> str:
        """Generate a password reset token for the user"""
        try:
            # Verify user exists
            db_user = self.db.query(User).filter(User.email == email).first()
            if not db_user:
                # Don't reveal whether email exists
                return None
                
            # Create reset token that expires in 1 hour
            reset_data = {
                "sub": email,
                "type": "reset",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            }
            
            return jwt.encode(
                reset_data,
                self.session_driver.SECRET_KEY,
                algorithm=self.session_driver.ALGORITHM
            )
            
        except Exception as e:
            logger.error(f"Error generating reset token: {str(e)}")
            return None