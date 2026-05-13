from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatwootStatusResponse(BaseModel):
    chatwoot_configured: bool = Field(
        description="True when CHATWOOT_BASE_URL and CHATWOOT_PLATFORM_API_TOKEN are set."
    )
    subscription_active: bool
    chatwoot_provisioned: bool
    chatwoot_account_id: Optional[int] = None
    token_valid: Optional[bool] = Field(
        default=None,
        description="When provisioned, whether a lightweight Chatwoot API call succeeded.",
    )


class ChatwootChannelLinkResponse(BaseModel):
    channel: str
    chatwoot_account_id: int
    chatwoot_public_url: str
    authorization_url: str
    channel_hint: str
    chatwoot_login_ready: bool
    chatwoot_login: Dict[str, Any]
    autobus_meta_webhook_url: Optional[str] = None
    message: str


class ChatwootSessionResponse(BaseModel):
    chatwoot_account_id: int
    chatwoot_public_url: str
    authorization_url: str
    chatwoot_login_ready: bool
    chatwoot_login: Dict[str, Any]
    message: str


class ChatwootInboxesListResponse(BaseModel):
    inboxes: List[Dict[str, Any]]
    total: int
