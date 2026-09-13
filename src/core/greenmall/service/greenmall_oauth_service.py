"""GreenMall first-party linking — session state, callback URL, API key storage."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

try:
    import redis
except ImportError:  # pragma: no cover - optional at unit-test import time
    redis = None  # type: ignore[assignment]

from utilities.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

STATE_PREFIX = "gm."
STATE_TTL_SECONDS = 30 * 60
RESULT_TTL_SECONDS = 10 * 60
DEFAULT_AUTHORIZE_PATH = "/integrations/autobus/authorize"

_redis_client: Optional[Any] = None


def _redis() -> Optional["redis.Redis"]:
    global _redis_client
    if redis is None:
        return None
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
        logger.warning("[GREENMALL] Redis unavailable for OAuth state: %s", exc)
        return None


def public_api_base() -> str:
    return (
        os.getenv("AUTOBUS_PUBLIC_API_URL", "").strip()
        or os.getenv("PUBLIC_API_URL", "").strip()
        or "https://api.useautobus.com"
    ).rstrip("/")


def greenmall_callback_url() -> str:
    explicit = (os.getenv("GREENMALL_CALLBACK_URL") or "").strip()
    if explicit:
        return explicit
    return f"{public_api_base()}/api/v1/greenmall/callback"


def greenmall_api_base() -> str:
    return (os.getenv("GREENMALL_API_URL") or "").strip().rstrip("/")


def greenmall_authorize_url() -> str:
    explicit = (os.getenv("GREENMALL_AUTHORIZE_URL") or "").strip()
    if explicit:
        return explicit
    base = greenmall_api_base()
    if not base:
        return ""
    path = (os.getenv("GREENMALL_AUTHORIZE_PATH") or DEFAULT_AUTHORIZE_PATH).strip()
    if not path.startswith("/"):
        path = f"/{path}"
    return urljoin(f"{base}/", path.lstrip("/"))


def shared_secret() -> str:
    return (
        os.getenv("GREENMALL_CALLBACK_SECRET")
        or os.getenv("GREENMALL_SHARED_SECRET")
        or ""
    ).strip()


def outbound_secret() -> str:
    return (
        os.getenv("GREENMALL_SHARED_SECRET")
        or os.getenv("GREENMALL_CALLBACK_SECRET")
        or ""
    ).strip()


def debug_mode() -> bool:
    return os.getenv("DEBUG", "false").strip().lower() in ("1", "true", "yes", "on")


class GreenMallOAuthState:
    """One-time CSRF state that binds a GreenMall callback to an Autobus user."""

    _states: Dict[str, Dict[str, Any]] = {}
    _results: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _key(cls, state: str) -> str:
        return f"autobus:oauth:greenmall:{state}"

    @classmethod
    def _result_key(cls, state: str) -> str:
        return f"autobus:oauth:greenmall:result:{state}"

    @classmethod
    def create(cls, user_id: str) -> str:
        raw = secrets.token_urlsafe(32)
        state = f"{STATE_PREFIX}{raw}"
        payload = json.dumps({"user_id": user_id}, separators=(",", ":"))
        r = _redis()
        if r is not None:
            try:
                r.setex(cls._key(state), STATE_TTL_SECONDS, payload)
                return state
            except Exception as exc:
                logger.warning("[GREENMALL] Redis setex failed, using memory: %s", exc)
        cls._states[state] = {
            "value": payload,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=STATE_TTL_SECONDS),
        }
        return state

    @classmethod
    def peek(cls, state: Optional[str]) -> Optional[Dict[str, str]]:
        """Read session without consuming it (used before GreenMall authorize)."""
        if not state or not state.startswith(STATE_PREFIX):
            return None
        raw = None
        r = _redis()
        if r is not None:
            try:
                raw = r.get(cls._key(state))
            except Exception as exc:
                logger.warning("[GREENMALL] Redis get failed, trying memory: %s", exc)
        if raw is None:
            data = cls._states.get(state)
            if not data:
                return None
            if datetime.now(timezone.utc) > data["expires_at"]:
                cls._states.pop(state, None)
                return None
            raw = data.get("value")
        return cls._parse_payload(raw)

    @classmethod
    def consume(cls, state: Optional[str]) -> Optional[Dict[str, str]]:
        if not state or not state.startswith(STATE_PREFIX):
            return None
        raw = None
        r = _redis()
        if r is not None:
            try:
                key = cls._key(state)
                raw = r.get(key)
                if raw:
                    r.delete(key)
            except Exception as exc:
                logger.warning("[GREENMALL] Redis consume failed, trying memory: %s", exc)
                raw = None
        if raw is None:
            data = cls._states.pop(state, None)
            if not data:
                return None
            if datetime.now(timezone.utc) > data["expires_at"]:
                return None
            raw = data.get("value")
        return cls._parse_payload(raw)

    @classmethod
    def store_result(cls, state: str, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":"))
        r = _redis()
        if r is not None:
            try:
                r.setex(cls._result_key(state), RESULT_TTL_SECONDS, encoded)
                return
            except Exception as exc:
                logger.warning("[GREENMALL] Redis result setex failed: %s", exc)
        cls._results[state] = {
            "value": encoded,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=RESULT_TTL_SECONDS),
        }

    @classmethod
    def read_result(cls, state: Optional[str]) -> Optional[Dict[str, Any]]:
        if not state:
            return None
        raw = None
        r = _redis()
        if r is not None:
            try:
                raw = r.get(cls._result_key(state))
            except Exception as exc:
                logger.warning("[GREENMALL] Redis result get failed: %s", exc)
        if raw is None:
            data = cls._results.get(state)
            if not data:
                return None
            if datetime.now(timezone.utc) > data["expires_at"]:
                cls._results.pop(state, None)
                return None
            raw = data.get("value")
        try:
            parsed = json.loads(str(raw or ""))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _parse_payload(raw: Any) -> Optional[Dict[str, str]]:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        user_id = str((data or {}).get("user_id") or "").strip()
        if not user_id:
            return None
        return {"user_id": user_id}

    @classmethod
    def clear_memory(cls) -> None:
        cls._states.clear()
        cls._results.clear()


class GreenMallOAuthService:
    def encrypt_key(self, api_key: str) -> str:
        encrypted = encrypt_secret(api_key)
        if not encrypted:
            raise RuntimeError("Could not store the GreenMall API key.")
        return encrypted

    def decrypt_key(self, stored: str) -> str:
        return decrypt_secret(stored) or ""

    def require_authorize_url(self) -> str:
        url = greenmall_authorize_url()
        if not url:
            raise ValueError(
                "GreenMall is not configured. Set GREENMALL_API_URL (or "
                "GREENMALL_AUTHORIZE_URL) on the Autobus backend."
            )
        return url

    def verify_callback_secret(self, provided: Optional[str]) -> None:
        expected = shared_secret()
        if not expected:
            if debug_mode():
                return
            raise PermissionError(
                "GREENMALL_CALLBACK_SECRET is not configured on Autobus."
            )
        if not provided or not hmac.compare_digest(provided.strip(), expected):
            raise PermissionError("Invalid GreenMall callback secret.")

    def verify_callback_signature(self, raw_body: bytes, provided: Optional[str]) -> None:
        expected_secret = shared_secret()
        if not expected_secret or not provided:
            return
        digest = hmac.new(
            expected_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(digest, provided.strip()):
            raise PermissionError("Invalid GreenMall callback signature.")

    def fallback_store_id(self, *, store_email: str, api_key: str) -> str:
        material = (store_email or api_key).strip()
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
        return f"gm-{digest}"

    def authorize_on_greenmall(
        self,
        *,
        email: str,
        password: str,
        state: str,
        callback_url: str,
    ) -> Dict[str, Any]:
        """Ask GreenMall to authenticate the merchant and deliver an API key."""
        url = self.require_authorize_url()
        payload = {
            "email": email,
            "password": password,
            "state": state,
            "callback_url": callback_url,
        }
        headers = {"Content-Type": "application/json"}
        secret = outbound_secret()
        if secret:
            headers["X-Autobus-Secret"] = secret
            headers["X-GreenMall-Secret"] = secret
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            logger.exception("[GREENMALL] authorize request failed")
            raise RuntimeError(f"Could not reach GreenMall: {exc}") from exc

        if resp.status_code >= 400:
            detail = _response_detail(resp)
            logger.warning(
                "[GREENMALL] authorize rejected: %s %s",
                resp.status_code,
                detail,
            )
            if resp.status_code in (401, 403):
                raise PermissionError(detail or "GreenMall email or password is incorrect.")
            raise RuntimeError(detail or "GreenMall could not complete the link.")

        try:
            data = resp.json() if resp.content else {}
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {}


def _response_detail(resp: requests.Response) -> str:
    try:
        data = resp.json()
    except ValueError:
        text = (resp.text or "").strip()
        return text[:240]
    if isinstance(data, dict):
        for key in ("detail", "message", "error", "error_description"):
            value = data.get(key)
            if value:
                return str(value)
    return ""


def extract_api_key(payload: Dict[str, Any]) -> str:
    for key in ("api_key", "apiKey", "access_token", "accessToken", "token"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def extract_store_id(payload: Dict[str, Any]) -> str:
    for key in ("store_id", "storeId", "id", "merchant_id", "merchantId"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def extract_store_name(payload: Dict[str, Any]) -> str:
    for key in ("store_name", "storeName", "name", "business_name", "company"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def extract_store_email(payload: Dict[str, Any]) -> str:
    for key in ("store_email", "storeEmail", "email"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""
