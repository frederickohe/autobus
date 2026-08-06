"""Business Login for Instagram — OAuth authorize, token exchange, profile."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import redis
import requests

from utilities.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

DEFAULT_SCOPES = (
    "instagram_business_basic,"
    "instagram_business_manage_messages,"
    "instagram_business_manage_comments,"
    "instagram_business_content_publish,"
    "instagram_business_manage_insights"
)

STATE_PREFIX = "ig."
STATE_TTL_SECONDS = 30 * 60
_redis_client: Optional[redis.Redis] = None


def _redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        password = os.getenv("REDIS_PASSWORD") or None
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=password,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("[IG] Redis unavailable for OAuth state: %s", exc)
        return None


class InstagramOAuthState:
    """CSRF state for Instagram Business Login (Redis, in-memory fallback)."""

    _states: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _key(cls, state: str) -> str:
        return f"autobus:oauth:instagram:{state}"

    @classmethod
    def create(cls, user_id: str) -> str:
        raw = secrets.token_urlsafe(32)
        state = f"{STATE_PREFIX}{raw}"
        r = _redis()
        if r is not None:
            try:
                r.setex(cls._key(state), STATE_TTL_SECONDS, user_id)
                return state
            except Exception as exc:
                logger.warning("[IG] Redis setex failed, using memory: %s", exc)
        cls._states[state] = {
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=STATE_TTL_SECONDS),
        }
        return state

    @classmethod
    def validate(cls, state: str) -> Optional[str]:
        if not state or not state.startswith(STATE_PREFIX):
            return None
        r = _redis()
        if r is not None:
            try:
                key = cls._key(state)
                user_id = r.get(key)
                if user_id:
                    r.delete(key)
                    return str(user_id)
            except Exception as exc:
                logger.warning("[IG] Redis get failed, trying memory: %s", exc)
        data = cls._states.get(state)
        if not data:
            return None
        if datetime.now(timezone.utc) > data["expires_at"]:
            cls._states.pop(state, None)
            return None
        cls._states.pop(state, None)
        return data["user_id"]

    @classmethod
    def is_instagram_state(cls, state: Optional[str]) -> bool:
        return bool(state and state.startswith(STATE_PREFIX))


class InstagramOAuthService:
    def __init__(self) -> None:
        self.app_id = (
            os.getenv("INSTAGRAM_APP_ID")
            or os.getenv("META_INSTAGRAM_APP_ID")
            or ""
        ).strip()
        self.app_secret = (
            os.getenv("INSTAGRAM_APP_SECRET")
            or os.getenv("META_INSTAGRAM_APP_SECRET")
            or os.getenv("META_APP_SECRET")
            or ""
        ).strip()
        self.redirect_uri = (
            os.getenv("INSTAGRAM_REDIRECT_URI")
            or os.getenv("META_INSTAGRAM_REDIRECT_URI")
            or os.getenv("META_WHATSAPP_REDIRECT_URI")
            or "https://useautobus.com/api/social/callback"
        ).strip()
        self.scopes = (os.getenv("INSTAGRAM_OAUTH_SCOPES") or DEFAULT_SCOPES).strip()
        self.graph_base = (
            os.getenv("INSTAGRAM_GRAPH_BASE_URL") or "https://graph.instagram.com"
        ).rstrip("/")
        self.oauth_base = (
            os.getenv("INSTAGRAM_OAUTH_BASE_URL") or "https://www.instagram.com"
        ).rstrip("/")
        self.api_oauth_base = (
            os.getenv("INSTAGRAM_API_OAUTH_BASE_URL") or "https://api.instagram.com"
        ).rstrip("/")

    def require_config(self) -> None:
        missing = [
            name
            for name, val in (
                ("INSTAGRAM_APP_ID", self.app_id),
                ("INSTAGRAM_APP_SECRET (or META_APP_SECRET)", self.app_secret),
            )
            if not val
        ]
        if missing:
            raise ValueError(f"Instagram OAuth config missing: {', '.join(missing)}")

    def build_authorize_url(self, state: str) -> str:
        self.require_config()
        params = {
            "force_reauth": "true",
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
            "state": state,
        }
        return f"{self.oauth_base}/oauth/authorize?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for short-lived Instagram User token."""
        self.require_config()
        clean_code = (code or "").split("#")[0].strip()
        url = f"{self.api_oauth_base}/oauth/access_token"
        payload = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": clean_code,
        }
        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code >= 400:
            logger.error(
                "[IG] short-lived token exchange failed: %s %s",
                resp.status_code,
                resp.text[:500],
            )
            resp.raise_for_status()
        data = resp.json()
        if isinstance(data.get("data"), list) and data["data"]:
            data = data["data"][0]
        if not data.get("access_token"):
            raise RuntimeError(
                f"Instagram token exchange returned no access_token: {data}"
            )
        return data

    def exchange_long_lived(self, short_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for ~60-day long-lived token."""
        self.require_config()
        url = f"{self.graph_base}/access_token"
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": self.app_secret,
            "access_token": short_token,
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code >= 400:
            logger.warning(
                "[IG] long-lived exchange failed (%s): %s — keeping short-lived token",
                resp.status_code,
                resp.text[:300],
            )
            return {"access_token": short_token}
        data = resp.json()
        if not data.get("access_token"):
            return {"access_token": short_token}
        return data

    def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        url = f"{self.graph_base}/me"
        params = {
            "fields": "id,username,name,account_type,profile_picture_url",
            "access_token": access_token,
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code >= 400:
            logger.error("[IG] /me failed: %s %s", resp.status_code, resp.text[:400])
            resp.raise_for_status()
        return resp.json()

    def encrypt_token(self, token: str) -> str:
        encrypted = encrypt_secret(token)
        if encrypted is None:
            raise RuntimeError("Failed to encrypt Instagram access token")
        return encrypted

    def decrypt_token(self, encrypted: str) -> str:
        plain = decrypt_secret(encrypted)
        if not plain:
            raise RuntimeError("Failed to decrypt Instagram access token")
        return plain

    @staticmethod
    def permissions_list(raw: Any) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return [p.strip() for p in str(raw).split(",") if p.strip()]

    @staticmethod
    def token_expiry(expires_in: Optional[Any]) -> Optional[datetime]:
        try:
            seconds = int(expires_in) if expires_in is not None else None
        except (TypeError, ValueError):
            seconds = None
        if not seconds:
            seconds = 60 * 24 * 3600
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)
