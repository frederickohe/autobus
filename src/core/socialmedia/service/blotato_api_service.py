"""
Blotato API Integration Service
Handles OAuth flow and API calls to Blotato for social media management
"""

import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import secrets
import json
from functools import lru_cache

logger = logging.getLogger(__name__)


class BlotatoAPIClient:
    """
    Client for interacting with Blotato API.
    Handles OAuth flow and post publishing.
    """
    
    # Blotato API endpoints
    BLOTATO_API_BASE = "https://api.blotato.com"
    BLOTATO_OAUTH_BASE = "https://app.blotato.com"
    
    # Endpoints
    OAUTH_AUTHORIZE_URL = f"{BLOTATO_OAUTH_BASE}/oauth/authorize"
    OAUTH_TOKEN_URL = f"{BLOTATO_API_BASE}/v1/oauth/token"
    GET_ACCOUNTS_URL = f"{BLOTATO_API_BASE}/v1/accounts"
    MEDIA_UPLOAD_URL = f"{BLOTATO_API_BASE}/v2/media-upload/url"
    CREATE_POST_URL = f"{BLOTATO_API_BASE}/v2/posts"
    
    # Rate limits
    POSTS_PER_MINUTE = 30
    MEDIA_UPLOADS_PER_MINUTE = 10
    MAX_MEDIA_SIZE_MB = 60
    
    def __init__(self, api_key: str, client_id: str, client_secret: str):
        """
        Initialize Blotato API Client
        
        Args:
            api_key: Blotato API key for server-to-server calls
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = 30
        
    def _get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "blotato-api-key": self.api_key,
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers
    
    async def generate_oauth_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL for user
        
        Args:
            redirect_uri: Callback URL after user authorizes
            state: Optional state for CSRF protection (generated if not provided)
            
        Returns:
            Tuple of (authorization_url, state)
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "accounts:read posts:write media:upload"  # Requested scopes
        }
        
        # Build URL with params
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.OAUTH_AUTHORIZE_URL}?{query_string}"
        
        logger.info(f"[BLOTATO] Generated OAuth URL")
        return auth_url, state
    
    async def exchange_auth_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for account information
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Callback URL used in initial authorization
            
        Returns:
            Dictionary with account info or None if failed
        """
        try:
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OAUTH_TOKEN_URL,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    logger.info(f"[BLOTATO] Successfully exchanged auth code")
                    return token_data
                else:
                    logger.error(f"[BLOTATO] OAuth token exchange failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[BLOTATO] Error exchanging auth code: {str(e)}")
            return None
    
    async def get_accounts(self, access_token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of connected accounts for user
        
        Args:
            access_token: User's access token from OAuth
            
        Returns:
            List of account dictionaries or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.GET_ACCOUNTS_URL,
                    headers=self._get_headers(access_token),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    accounts = response.json()
                    logger.info(f"[BLOTATO] Retrieved {len(accounts)} accounts")
                    return accounts if isinstance(accounts, list) else accounts.get("accounts", [])
                else:
                    logger.error(f"[BLOTATO] Get accounts failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[BLOTATO] Error getting accounts: {str(e)}")
            return None
    
    async def upload_media(self, media_url: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Upload media from URL to Blotato
        
        Args:
            media_url: URL of media to upload
            access_token: User's access token
            
        Returns:
            Media info with media_id or None if failed
        """
        try:
            payload = {
                "url": media_url
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.MEDIA_UPLOAD_URL,
                    json=payload,
                    headers=self._get_headers(access_token),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    media_info = response.json()
                    logger.info(f"[BLOTATO] Media uploaded successfully: {media_info.get('media_id')}")
                    return media_info
                else:
                    logger.error(f"[BLOTATO] Media upload failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[BLOTATO] Error uploading media: {str(e)}")
            return None
    
    async def create_post(
        self,
        account_id: str,
        content: str,
        access_token: str,
        media_ids: Optional[List[str]] = None,
        schedule_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a post on a social media account
        
        Args:
            account_id: Blotato account ID to post to
            content: Post content/text
            access_token: User's access token
            media_ids: Optional list of media IDs to attach
            schedule_time: Optional ISO datetime for scheduled posts
            
        Returns:
            Post info with post_id or None if failed
        """
        try:
            payload = {
                "accountId": account_id,
                "content": content,
            }
            
            if media_ids:
                payload["media"] = media_ids
            
            if schedule_time:
                payload["publishDate"] = schedule_time
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.CREATE_POST_URL,
                    json=payload,
                    headers=self._get_headers(access_token),
                    timeout=self.timeout
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    post_info = response.json()
                    logger.info(f"[BLOTATO] Post created successfully: {post_info.get('post_id')}")
                    return post_info
                else:
                    logger.error(f"[BLOTATO] Create post failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[BLOTATO] Error creating post: {str(e)}")
            return None
    
    async def validate_rate_limit(self, last_request_time: Optional[datetime], requests_count: int) -> bool:
        """
        Validate if request is within rate limits
        
        Args:
            last_request_time: Last request timestamp
            requests_count: Number of requests in current minute
            
        Returns:
            True if within limits, False otherwise
        """
        if not last_request_time:
            return True
        
        time_diff = datetime.utcnow() - last_request_time
        
        # If more than a minute has passed, reset counter
        if time_diff.total_seconds() > 60:
            return True
        
        # Check if still within rate limit
        return requests_count < self.POSTS_PER_MINUTE


class BlotatoOAuthManager:
    """Manages OAuth state and validation"""
    
    # Store states in memory (in production, use Redis)
    _oauth_states: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_state(cls, user_id: str, platform: str) -> str:
        """
        Create an OAuth state for CSRF protection
        
        Args:
            user_id: User ID
            platform: Social media platform
            
        Returns:
            State token
        """
        state = secrets.token_urlsafe(32)
        cls._oauth_states[state] = {
            "user_id": user_id,
            "platform": platform,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        logger.info(f"[OAUTH] Created state for user {user_id}, platform {platform}")
        return state
    
    @classmethod
    def validate_state(cls, state: str) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth state and return associated data
        
        Args:
            state: State token to validate
            
        Returns:
            State data or None if invalid/expired
        """
        state_data = cls._oauth_states.get(state)
        
        if not state_data:
            logger.warning(f"[OAUTH] Invalid state: {state}")
            return None
        
        if datetime.utcnow() > state_data["expires_at"]:
            logger.warning(f"[OAUTH] Expired state: {state}")
            del cls._oauth_states[state]
            return None
        
        # Remove used state
        del cls._oauth_states[state]
        logger.info(f"[OAUTH] State validated for user {state_data['user_id']}")
        return state_data
