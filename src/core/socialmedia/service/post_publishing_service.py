"""
Post Publishing Service
Handles publishing content to multiple social media platforms via Blotato
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.socialmedia.model.SocialAccount import SocialAccount
from core.socialmedia.service.blotato_api_service import BlotatoAPIClient
from core.socialmedia.service.socialmedia_service import SocialMediaService
from core.socialmedia.dto.socialmedia_dto import (
    PublishPostRequest, PlatformPublishResult, PublishPostResponse,
    PublishMediaItem
)

logger = logging.getLogger(__name__)


class PostPublishingService:
    """Service for publishing posts to social media"""
    
    def __init__(self, db: Session, blotato_client: BlotatoAPIClient):
        """
        Initialize service
        
        Args:
            db: Database session
            blotato_client: Blotato API client instance
        """
        self.db = db
        self.blotato_client = blotato_client
        self.social_service = SocialMediaService(db, blotato_client)
    
    async def publish_post(
        self,
        user_id: str,
        publish_request: PublishPostRequest,
        access_token: Optional[str] = None
    ) -> PublishPostResponse:
        """
        Publish post to multiple social media accounts
        
        Args:
            user_id: User ID
            publish_request: Post content and target accounts
            access_token: Optional Blotato access token (for uploading media)
            
        Returns:
            PublishPostResponse with results for each platform
        """
        results: List[PlatformPublishResult] = []
        successful_posts = 0
        
        try:
            # Validate account ownership
            valid, error_msg = self.social_service.validate_account_ownership(
                publish_request.account_ids,
                user_id
            )
            
            if not valid:
                return PublishPostResponse(
                    success=False,
                    total_platforms=0,
                    successful_posts=0,
                    failed_posts=len(publish_request.account_ids),
                    results=[],
                    message=error_msg or "Account validation failed"
                )
            
            # Get all accounts
            accounts = {
                acc.id: acc for acc in self.social_service.get_user_accounts(user_id)
            }
            
            # Upload media if provided
            media_ids = []
            if publish_request.media_urls and access_token:
                for media_item in publish_request.media_urls:
                    media_result = await self._upload_media(
                        media_item.url,
                        access_token
                    )
                    if media_result:
                        media_ids.append(media_result.get("media_id") or media_result.get("url"))
            
            # Publish to each account
            for account_id in publish_request.account_ids:
                account = accounts.get(account_id)
                if not account:
                    continue
                
                result = await self._publish_to_platform(
                    account=account,
                    content=publish_request.content,
                    media_ids=media_ids,
                    schedule_time=publish_request.schedule_time,
                    access_token=access_token
                )
                
                results.append(result)
                
                if result.success:
                    successful_posts += 1
                    # Update last_used timestamp
                    await self.social_service.update_last_used(account_id, user_id)
            
            # Determine overall success
            failed_posts = len(publish_request.account_ids) - successful_posts
            overall_success = failed_posts == 0
            
            message = self._build_response_message(
                successful_posts,
                failed_posts,
                len(publish_request.account_ids)
            )
            
            logger.info(f"[PUBLISH] Post published by user {user_id}: {successful_posts}/{len(publish_request.account_ids)} successful")
            
            return PublishPostResponse(
                success=overall_success,
                total_platforms=len(publish_request.account_ids),
                successful_posts=successful_posts,
                failed_posts=failed_posts,
                results=results,
                message=message
            )
            
        except Exception as e:
            logger.error(f"[PUBLISH] Error publishing post: {str(e)}")
            return PublishPostResponse(
                success=False,
                total_platforms=len(publish_request.account_ids),
                successful_posts=0,
                failed_posts=len(publish_request.account_ids),
                results=results,
                message=f"Error publishing post: {str(e)}"
            )
    
    async def _upload_media(self, media_url: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Upload media to Blotato
        
        Args:
            media_url: URL of media to upload
            access_token: User's access token
            
        Returns:
            Media info or None if failed
        """
        try:
            media_info = await self.blotato_client.upload_media(media_url, access_token)
            return media_info
        except Exception as e:
            logger.error(f"[PUBLISH] Media upload error: {str(e)}")
            return None
    
    async def _publish_to_platform(
        self,
        account: SocialAccount,
        content: str,
        media_ids: Optional[List[str]] = None,
        schedule_time: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> PlatformPublishResult:
        """
        Publish to a specific platform
        
        Args:
            account: Social account to publish to
            content: Post content
            media_ids: List of media IDs
            schedule_time: Optional schedule time
            access_token: User's access token
            
        Returns:
            PlatformPublishResult with status
        """
        try:
            # Use account's access token if available, fallback to provided token
            token = access_token or account.access_token
            
            if not token:
                return PlatformPublishResult(
                    account_id=account.id,
                    platform=account.platform,
                    success=False,
                    error="No access token available",
                    message="Access token not available for this account"
                )
            
            # Check rate limits
            if account.posts_today >= self.blotato_client.POSTS_PER_MINUTE:
                return PlatformPublishResult(
                    account_id=account.id,
                    platform=account.platform,
                    success=False,
                    error="Rate limit exceeded",
                    message=f"Daily post limit reached for {account.platform}"
                )
            
            # Create post via Blotato API
            post_result = await self.blotato_client.create_post(
                account_id=account.account_id,
                content=content,
                access_token=token,
                media_ids=media_ids,
                schedule_time=schedule_time
            )
            
            if post_result:
                # Update account stats
                account.posts_today += 1
                account.last_post_time = datetime.utcnow()
                self.db.commit()
                
                return PlatformPublishResult(
                    account_id=account.id,
                    platform=account.platform,
                    success=True,
                    post_id=post_result.get("post_id") or post_result.get("id"),
                    message="Posted successfully"
                )
            else:
                return PlatformPublishResult(
                    account_id=account.id,
                    platform=account.platform,
                    success=False,
                    error="API error",
                    message="Failed to publish to Blotato API"
                )
                
        except Exception as e:
            logger.error(f"[PUBLISH] Error publishing to {account.platform}: {str(e)}")
            return PlatformPublishResult(
                account_id=account.id,
                platform=account.platform,
                success=False,
                error=str(e),
                message=f"Error publishing: {str(e)}"
            )
    
    def _build_response_message(self, successful: int, failed: int, total: int) -> str:
        """Build user-friendly response message"""
        if failed == 0:
            return f"All {total} posts published successfully"
        elif successful == 0:
            return f"Failed to publish to all {total} platforms"
        else:
            return f"Published to {successful}/{total} platforms ({failed} failed)"
