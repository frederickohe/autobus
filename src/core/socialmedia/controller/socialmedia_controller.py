"""
Social Media Controller
API routes for social media account management and posting
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from fastapi_jwt_auth import AuthJWT
from core.socialmedia.dto.socialmedia_dto import (
    SocialAccountResponse, SocialAccountsListResponse, DisconnectAccountRequest,
    PublishPostRequest, PublishPostResponse, RefreshAccountsRequest,
    RefreshAccountsResponse, OAuth2CallbackRequest, ErrorResponse,
    SocialPlatformEnum
)
from core.socialmedia.service.socialmedia_service import SocialMediaService
from core.socialmedia.service.post_publishing_service import PostPublishingService
from core.socialmedia.service.blotato_api_service import (
    BlotatoAPIClient, BlotatoOAuthManager
)
from utilities.dbconfig import get_db

logger = logging.getLogger(__name__)

# Initialize router
social_routes = APIRouter()

# Initialize Blotato API Client (with environment variables)
BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY", "")
BLOTATO_CLIENT_ID = os.getenv("BLOTATO_CLIENT_ID", "")
BLOTATO_CLIENT_SECRET = os.getenv("BLOTATO_CLIENT_SECRET", "")

if not all([BLOTATO_API_KEY, BLOTATO_CLIENT_ID, BLOTATO_CLIENT_SECRET]):
    logger.warning("[SOCIAL] Blotato credentials not fully configured in environment variables")

blotato_client = BlotatoAPIClient(
    api_key=BLOTATO_API_KEY,
    client_id=BLOTATO_CLIENT_ID,
    client_secret=BLOTATO_CLIENT_SECRET
)


# Dependency for token validation
def validate_token(authjwt: AuthJWT = Depends()) -> str:
    """Validate JWT token and return user ID"""
    try:
        authjwt.jwt_required()
        return authjwt.get_jwt_subject()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ==================== OAuth Flow Routes ====================

@social_routes.get("/connect/{platform}")
async def initiate_oauth_flow(
    platform: str,
    user_id: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth flow for connecting a social media account
    
    Args:
        platform: Social media platform (twitter, linkedin, facebook, instagram, tiktok, etc.)
        user_id: Authenticated user ID
        
    Returns:
        Redirect URL to Blotato OAuth endpoint
    """
    try:
        # Normalize platform
        platform_upper = platform.upper()
        
        # Validate platform
        valid_platforms = [p.value for p in SocialPlatformEnum]
        if platform_upper not in valid_platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform. Supported: {', '.join(valid_platforms)}"
            )
        
        # Create OAuth state for CSRF protection
        state = BlotatoOAuthManager.create_state(user_id, platform_upper)
        
        # Generate OAuth URL
        callback_url = f"{os.getenv('BASE_FRONTEND_URL', 'http://localhost:3000')}/api/social/callback"
        auth_url, _ = await blotato_client.generate_oauth_url(
            redirect_uri=callback_url,
            state=state
        )
        
        logger.info(f"[SOCIAL] OAuth flow initiated for user {user_id}, platform {platform_upper}")
        
        return {
            "authorization_url": auth_url,
            "platform": platform_upper,
            "message": "Redirect user to this URL to authorize account connection"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL] Error initiating OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initiating OAuth: {str(e)}"
        )


@social_routes.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Blotato
    
    Args:
        code: Authorization code from Blotato
        state: State parameter for CSRF validation
        error: Error code if user denied authorization
        error_description: Error description
        
    Returns:
        Account connection status
    """
    try:
        # Check for errors
        if error:
            logger.warning(f"[SOCIAL] OAuth error: {error} - {error_description}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authorization failed: {error_description or error}"
            )
        
        # Validate state
        state_data = BlotatoOAuthManager.validate_state(state)
        if not state_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter"
            )
        
        user_id = state_data["user_id"]
        platform = state_data["platform"]
        
        # Exchange code for account info
        callback_url = f"{os.getenv('BASE_FRONTEND_URL', 'http://localhost:3000')}/api/social/callback"
        token_data = await blotato_client.exchange_auth_code(code, callback_url)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
        
        # Get accounts from Blotato
        access_token = token_data.get("access_token")
        accounts = await blotato_client.get_accounts(access_token)
        
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve accounts from Blotato"
            )
        
        # Find account for this platform
        platform_account = next(
            (acc for acc in accounts if acc.get("platform", "").upper() == platform),
            None
        )
        
        if not platform_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No {platform} account found in Blotato"
            )
        
        # Store account in database
        social_service = SocialMediaService(db, blotato_client)
        success, account_obj, message = await social_service.connect_account(
            user_id=user_id,
            platform=platform,
            blotato_account_info=platform_account
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info(f"[SOCIAL] OAuth callback successful: {user_id} - {platform}")
        
        return {
            "success": True,
            "message": f"Account connected successfully",
            "platform": platform,
            "account_name": account_obj.account_name if account_obj else None,
            "redirect_url": f"{os.getenv('BASE_FRONTEND_URL', 'http://localhost:3000')}/social/accounts?connected=true"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL] Error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Callback processing error: {str(e)}"
        )


# ==================== Account Management Routes ====================

@social_routes.get("/accounts", response_model=SocialAccountsListResponse)
async def get_user_accounts(
    user_id: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Get all connected social media accounts for the user
    
    Returns:
        List of connected social accounts
    """
    try:
        social_service = SocialMediaService(db, blotato_client)
        accounts = social_service.get_user_accounts(user_id)
        
        logger.info(f"[SOCIAL] Retrieved {len(accounts)} accounts for user {user_id}")
        
        account_responses = [
            SocialAccountResponse.from_orm(acc) for acc in accounts
        ]
        
        return SocialAccountsListResponse(
            accounts=account_responses,
            total=len(account_responses)
        )
        
    except Exception as e:
        logger.error(f"[SOCIAL] Error getting accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving accounts: {str(e)}"
        )


@social_routes.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    request: DisconnectAccountRequest,
    user_id: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Disconnect a social media account
    
    Args:
        account_id: ID of account to disconnect
        request: Request body with disconnect options
        user_id: Authenticated user ID
        
    Returns:
        Disconnection status
    """
    try:
        social_service = SocialMediaService(db, blotato_client)
        success, message = await social_service.disconnect_account(account_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message
            )
        
        logger.info(f"[SOCIAL] Account disconnected: {account_id} by user {user_id}")
        
        return {
            "success": True,
            "message": message,
            "account_id": account_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL] Error disconnecting account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disconnecting account: {str(e)}"
        )


@social_routes.post("/refresh", response_model=RefreshAccountsResponse)
async def refresh_accounts(
    request: RefreshAccountsRequest,
    user_id: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Refresh user's connected accounts from Blotato
    
    Args:
        request: Refresh request with optional platform filter
        user_id: Authenticated user ID
        
    Returns:
        Updated list of connected accounts
    """
    try:
        # Get user's existing accounts to retrieve access token
        social_service = SocialMediaService(db, blotato_client)
        user_accounts = social_service.get_user_accounts(user_id)
        
        # Get access token from first account (or find from Blotato)
        # In production, store access token securely for the user
        if not user_accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No connected accounts found. Please connect an account first."
            )
        
        # Use first account's token as fallback
        access_token = user_accounts[0].access_token
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No valid access token found. Please reconnect your accounts."
            )
        
        # Refresh accounts
        success, accounts, message = await social_service.refresh_accounts(
            user_id=user_id,
            access_token=access_token,
            platforms=request.platforms
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info(f"[SOCIAL] Refreshed accounts for user {user_id}: {message}")
        
        account_responses = [
            SocialAccountResponse.from_orm(acc) for acc in accounts
        ]
        
        return RefreshAccountsResponse(
            success=True,
            refreshed_count=len(account_responses),
            accounts=account_responses,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOCIAL] Error refreshing accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing accounts: {str(e)}"
        )


# ==================== Post Publishing Routes ====================

@social_routes.post("/post", response_model=PublishPostResponse)
async def publish_post(
    request: PublishPostRequest,
    user_id: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Publish content to one or more connected social media accounts
    
    Args:
        request: Post content and target accounts
        user_id: Authenticated user ID
        
    Returns:
        Publishing results for each platform
    """
    try:
        # Get user's access token for media uploads
        social_service = SocialMediaService(db, blotato_client)
        user_accounts = social_service.get_user_accounts(user_id)
        
        access_token = None
        if user_accounts:
            access_token = user_accounts[0].access_token
        
        # Publish post
        publishing_service = PostPublishingService(db, blotato_client)
        response = await publishing_service.publish_post(
            user_id=user_id,
            publish_request=request,
            access_token=access_token
        )
        
        logger.info(f"[SOCIAL] Post published by user {user_id}: {response.successful_posts}/{response.total_platforms} successful")
        
        return response
        
    except Exception as e:
        logger.error(f"[SOCIAL] Error publishing post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error publishing post: {str(e)}"
        )
