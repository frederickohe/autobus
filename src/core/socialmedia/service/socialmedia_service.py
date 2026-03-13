"""
Social Media Account Service
Handles database operations and business logic for social media accounts
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from core.socialmedia.model.SocialAccount import SocialAccount, SocialPlatform
from core.socialmedia.service.blotato_api_service import BlotatoAPIClient
from core.socialmedia.dto.socialmedia_dto import (
    SocialAccountResponse, BlotatoAccountInfo, PublishMediaItem
)

logger = logging.getLogger(__name__)


class SocialMediaService:
    """Service for managing social media accounts and posts"""
    
    def __init__(self, db: Session, blotato_client: BlotatoAPIClient):
        """
        Initialize service
        
        Args:
            db: Database session
            blotato_client: Blotato API client instance
        """
        self.db = db
        self.blotato_client = blotato_client
    
    def _generate_account_id(self) -> str:
        """Generate unique social account ID"""
        return f"sa_{str(uuid.uuid4())[:12]}"
    
    async def connect_account(
        self,
        user_id: str,
        platform: str,
        blotato_account_info: Dict[str, Any]
    ) -> Tuple[bool, Optional[SocialAccount], str]:
        """
        Store connected account from OAuth callback
        
        Args:
            user_id: User ID
            platform: Platform name
            blotato_account_info: Account info from Blotato
            
        Returns:
            Tuple of (success, account_object, message)
        """
        try:
            # Generate unique ID
            account_id = self._generate_account_id()
            
            # Extract info from Blotato response
            blotato_account_id = blotato_account_info.get("account_id") or blotato_account_info.get("accountId")
            account_name = blotato_account_info.get("account_name") or blotato_account_info.get("accountName") or "Unknown"
            platform_user_id = blotato_account_info.get("platform_user_id") or blotato_account_info.get("platformUserId")
            access_token = blotato_account_info.get("access_token")
            refresh_token = blotato_account_info.get("refresh_token")
            
            # Check if account already exists
            existing = self.db.query(SocialAccount).filter(
                and_(
                    SocialAccount.user_id == user_id,
                    SocialAccount.platform == platform,
                    SocialAccount.account_id == blotato_account_id
                )
            ).first()
            
            if existing:
                logger.info(f"[SOCIAL] Account already exists: {user_id} - {platform} - {blotato_account_id}")
                return True, existing, "Account already connected"
            
            # Create new account record
            social_account = SocialAccount(
                id=account_id,
                user_id=user_id,
                platform=platform,
                account_id=blotato_account_id,
                account_name=account_name,
                platform_user_id=platform_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_active=True
            )
            
            self.db.add(social_account)
            self.db.commit()
            self.db.refresh(social_account)
            
            logger.info(f"[SOCIAL] Connected account: {user_id} - {platform} - {account_name}")
            return True, social_account, "Account connected successfully"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[SOCIAL] Error connecting account: {str(e)}")
            return False, None, f"Error connecting account: {str(e)}"
    
    def get_user_accounts(self, user_id: str) -> List[SocialAccount]:
        """
        Get all connected accounts for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of social accounts
        """
        try:
            accounts = self.db.query(SocialAccount).filter(
                SocialAccount.user_id == user_id
            ).all()
            logger.info(f"[SOCIAL] Retrieved {len(accounts)} accounts for user {user_id}")
            return accounts
        except Exception as e:
            logger.error(f"[SOCIAL] Error getting user accounts: {str(e)}")
            return []
    
    def get_user_accounts_by_platform(self, user_id: str, platform: str) -> List[SocialAccount]:
        """
        Get connected accounts for user by platform
        
        Args:
            user_id: User ID
            platform: Platform name
            
        Returns:
            List of social accounts for platform
        """
        try:
            accounts = self.db.query(SocialAccount).filter(
                and_(
                    SocialAccount.user_id == user_id,
                    SocialAccount.platform == platform,
                    SocialAccount.is_active == True
                )
            ).all()
            logger.info(f"[SOCIAL] Retrieved {len(accounts)} {platform} accounts for user {user_id}")
            return accounts
        except Exception as e:
            logger.error(f"[SOCIAL] Error getting platform accounts: {str(e)}")
            return []
    
    def get_account_by_id(self, account_id: str, user_id: str) -> Optional[SocialAccount]:
        """
        Get specific account by ID (verify ownership)
        
        Args:
            account_id: Social account ID
            user_id: User ID (for ownership check)
            
        Returns:
            Social account or None
        """
        try:
            account = self.db.query(SocialAccount).filter(
                and_(
                    SocialAccount.id == account_id,
                    SocialAccount.user_id == user_id
                )
            ).first()
            return account
        except Exception as e:
            logger.error(f"[SOCIAL] Error getting account by ID: {str(e)}")
            return None
    
    async def disconnect_account(self, account_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Disconnect a social account (local only)
        
        Args:
            account_id: Social account ID
            user_id: User ID (for ownership verification)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            account = self.get_account_by_id(account_id, user_id)
            
            if not account:
                return False, "Account not found or not owned by user"
            
            # Delete account record
            self.db.delete(account)
            self.db.commit()
            
            logger.info(f"[SOCIAL] Disconnected account: {user_id} - {account.platform}")
            return True, "Account disconnected successfully"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[SOCIAL] Error disconnecting account: {str(e)}")
            return False, f"Error disconnecting account: {str(e)}"
    
    async def refresh_accounts(self, user_id: str, access_token: str, platforms: Optional[List[str]] = None) -> Tuple[bool, List[SocialAccount], str]:
        """
        Refresh user's accounts from Blotato
        
        Args:
            user_id: User ID
            access_token: User's Blotato access token
            platforms: Optional list of platforms to refresh
            
        Returns:
            Tuple of (success, accounts_list, message)
        """
        try:
            # Get accounts from Blotato
            blotato_accounts = await self.blotato_client.get_accounts(access_token)
            
            if blotato_accounts is None:
                return False, [], "Failed to refresh accounts from Blotato"
            
            # Filter by platforms if specified
            if platforms:
                blotato_accounts = [
                    acc for acc in blotato_accounts
                    if acc.get("platform", "").upper() in [p.upper() for p in platforms]
                ]
            
            # Update or create accounts
            updated_count = 0
            for account_info in blotato_accounts:
                platform = account_info.get("platform", "UNKNOWN").upper()
                blotato_id = account_info.get("account_id") or account_info.get("accountId")
                
                # Try to find existing account
                existing = self.db.query(SocialAccount).filter(
                    and_(
                        SocialAccount.user_id == user_id,
                        SocialAccount.account_id == blotato_id
                    )
                ).first()
                
                if existing:
                    # Update existing
                    existing.account_name = account_info.get("account_name", existing.account_name)
                    existing.platform_user_id = account_info.get("platform_user_id", existing.platform_user_id)
                    existing.access_token = account_info.get("access_token", existing.access_token)
                    existing.refresh_token = account_info.get("refresh_token", existing.refresh_token)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    await self.connect_account(user_id, platform, account_info)
                
                updated_count += 1
            
            self.db.commit()
            
            # Get updated accounts
            accounts = self.get_user_accounts(user_id)
            message = f"Refreshed {updated_count} accounts"
            
            logger.info(f"[SOCIAL] Refreshed accounts for user {user_id}: {message}")
            return True, accounts, message
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[SOCIAL] Error refreshing accounts: {str(e)}")
            return False, [], f"Error refreshing accounts: {str(e)}"
    
    async def update_last_used(self, account_id: str, user_id: str) -> None:
        """
        Update last_used_at timestamp for account
        
        Args:
            account_id: Social account ID
            user_id: User ID
        """
        try:
            account = self.get_account_by_id(account_id, user_id)
            if account:
                account.last_used_at = datetime.utcnow()
                self.db.commit()
        except Exception as e:
            logger.error(f"[SOCIAL] Error updating last_used: {str(e)}")
    
    def validate_account_ownership(self, account_ids: List[str], user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that all account IDs belong to user
        
        Args:
            account_ids: List of account IDs to validate
            user_id: User ID
            
        Returns:
            Tuple of (all_valid, error_message)
        """
        for account_id in account_ids:
            account = self.get_account_by_id(account_id, user_id)
            if not account:
                return False, f"Account {account_id} not found or not owned by user"
            if not account.is_active:
                return False, f"Account {account_id} is not active"
        
        return True, None
