"""Meta WhatsApp Embedded Signup / Business App onboarding helpers."""

from __future__ import annotations

import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlencode

import redis
import requests

from utilities.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

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
        logger.warning("[WA] Redis unavailable for OAuth state: %s", exc)
        return None


class MetaWhatsAppOAuthState:
    """CSRF state for WhatsApp Embedded Signup (Redis, in-memory fallback)."""

    _states: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def normalize_return_to(return_to: Optional[str]) -> str:
        value = (return_to or "web").strip().lower()
        return "app" if value in {"app", "mobile", "ios", "android"} else "web"

    @classmethod
    def _key(cls, state: str) -> str:
        return f"autobus:oauth:whatsapp:{state}"

    @classmethod
    def _encode_payload(cls, user_id: str, return_to: str) -> str:
        return json.dumps(
            {"user_id": user_id, "return_to": cls.normalize_return_to(return_to)},
            separators=(",", ":"),
        )

    @classmethod
    def _parse_payload(cls, raw: Any) -> Optional[Dict[str, str]]:
        text = str(raw or "").strip()
        if not text:
            return None
        if text.startswith("{"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return None
            user_id = str((data or {}).get("user_id") or "").strip()
            if not user_id:
                return None
            return {
                "user_id": user_id,
                "return_to": cls.normalize_return_to((data or {}).get("return_to")),
            }
        return {"user_id": text, "return_to": "web"}

    @classmethod
    def create(cls, user_id: str, return_to: str = "web") -> str:
        state = secrets.token_urlsafe(32)
        payload = cls._encode_payload(user_id, return_to)
        r = _redis()
        if r is not None:
            try:
                r.setex(cls._key(state), STATE_TTL_SECONDS, payload)
                return state
            except Exception as exc:
                logger.warning("[WA] Redis setex failed, using memory: %s", exc)
        cls._states[state] = {
            "payload": payload,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc)
            + timedelta(seconds=STATE_TTL_SECONDS),
        }
        return state

    @classmethod
    def peek_payload(cls, state: str) -> Optional[Dict[str, str]]:
        """Return payload if state is valid without consuming it (launch page)."""
        if not state:
            return None
        r = _redis()
        if r is not None:
            try:
                raw = r.get(cls._key(state))
                parsed = cls._parse_payload(raw)
                if parsed:
                    return parsed
            except Exception as exc:
                logger.warning("[WA] Redis peek failed, trying memory: %s", exc)
        data = cls._states.get(state)
        if not data:
            return None
        if datetime.now(timezone.utc) > data["expires_at"]:
            cls._states.pop(state, None)
            return None
        return cls._parse_payload(data.get("payload") or data.get("user_id"))

    @classmethod
    def peek(cls, state: str) -> Optional[str]:
        """Return user_id if state is valid without consuming it (launch page)."""
        payload = cls.peek_payload(state)
        return payload["user_id"] if payload else None

    @classmethod
    def validate_payload(cls, state: str) -> Optional[Dict[str, str]]:
        """Consume state and return payload (callback / complete)."""
        if not state:
            return None
        r = _redis()
        if r is not None:
            try:
                key = cls._key(state)
                raw = r.get(key)
                parsed = cls._parse_payload(raw)
                if parsed:
                    r.delete(key)
                    return parsed
            except Exception as exc:
                logger.warning("[WA] Redis get failed, trying memory: %s", exc)
        data = cls._states.get(state)
        if not data:
            return None
        if datetime.now(timezone.utc) > data["expires_at"]:
            cls._states.pop(state, None)
            return None
        cls._states.pop(state, None)
        return cls._parse_payload(data.get("payload") or data.get("user_id"))

    @classmethod
    def validate(cls, state: str) -> Optional[str]:
        """Consume state and return user_id (callback / complete)."""
        payload = cls.validate_payload(state)
        return payload["user_id"] if payload else None


class MetaWhatsAppService:
    def __init__(self) -> None:
        self.app_id = (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()
        self.app_secret = (os.getenv("META_APP_SECRET") or "").strip()
        self.config_id = (os.getenv("META_WHATSAPP_CONFIG_ID") or "").strip()
        self.graph_base = (
            os.getenv("WHATSAPP_GRAPH_BASE_URL") or "https://graph.facebook.com/v25.0"
        ).rstrip("/")
        self.redirect_uri = (
            os.getenv("META_WHATSAPP_REDIRECT_URI")
            or "https://useautobus.com/api/social/callback"
        ).strip()
        self.platform_token = (os.getenv("META_API_KEY") or "").strip()
        self.default_pin = (os.getenv("WHATSAPP_REGISTER_PIN") or "123456").strip()

    def require_config(self) -> None:
        missing = [
            name
            for name, val in (
                ("META_APP_ID", self.app_id),
                ("META_APP_SECRET", self.app_secret),
                ("META_WHATSAPP_CONFIG_ID", self.config_id),
            )
            if not val
        ]
        if missing:
            raise ValueError(f"WhatsApp Meta config missing: {', '.join(missing)}")

    def build_onboard_url(self, state: str) -> str:
        """
        Direct Meta onboard URL (legacy / debug). Prefer build_launch_bridge_url —
        Embedded Signup is designed to be launched via the Facebook JS SDK from
        your own domain; opening Meta's onboard URL with redirect_uri often shows
        "This link is broken".
        """
        self.require_config()
        extras: Dict[str, Any] = {
            "setup": {},
            "sessionInfoVersion": (
                os.getenv("META_WHATSAPP_SESSION_INFO_VERSION") or "3"
            ).strip(),
        }
        feature_type = (os.getenv("META_WHATSAPP_FEATURE_TYPE") or "").strip()
        if feature_type:
            extras["featureType"] = feature_type
        version = (os.getenv("META_WHATSAPP_ES_VERSION") or "").strip()
        if version:
            extras["version"] = version

        # Match working partner implementations: no redirect_uri on this URL.
        # Completion is via FB.login code + postMessage (bridge page) or popup.
        params = {
            "app_id": self.app_id,
            "config_id": self.config_id,
            "response_type": "code",
            "scope": "whatsapp_business_messaging,whatsapp_business_management",
            "extras": json.dumps(extras, separators=(",", ":")),
        }
        return (
            "https://business.facebook.com/messaging/whatsapp/onboard/?"
            + urlencode(params)
        )

    def _public_base(self) -> str:
        return (os.getenv("BASE_FRONTEND_URL") or "https://useautobus.com").rstrip("/")

    def graph_version(self) -> str:
        version = self.graph_base.rstrip("/").split("/")[-1]
        return version if version.startswith("v") else "v21.0"

    def build_oauth_dialog_url(self, state: str) -> str:
        """
        Facebook Login for Business full-page dialog (no JS SDK / no popup).

        iOS Safari blocks FB.login() popups and often blocks connect.facebook.net,
        so the JS SDK bridge appears to load and then do nothing. This URL is the
        same redirect pattern Instagram uses and works in Safari / Chrome.
        """
        self.require_config()
        extras = json.dumps(self.embedded_signup_extras(), separators=(",", ":"))
        params = {
            "client_id": self.app_id,
            "config_id": self.config_id,
            "response_type": "code",
            "override_default_response_type": "true",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "extras": extras,
        }
        return f"https://www.facebook.com/{self.graph_version()}/dialog/oauth?{urlencode(params)}"

    def build_launch_bridge_url(self, state: str) -> str:
        """
        Autobus-hosted page that loads the Facebook JS SDK and calls FB.login
        with the Embedded Signup config_id (Meta's supported launch path).
        Served on useautobus.com so it matches App Domains / JS SDK allowlist.
        """
        self.require_config()
        return f"{self._public_base()}/api/v1/whatsapp/embedded-signup/launch?state={quote(state, safe='')}"

    def build_redirect_launch_url(self, state: str) -> str:
        """
        Autobus URL that 302s to the Facebook OAuth dialog.

        Starting on our domain then redirecting avoids iOS popup blockers and
        still presents facebook.com as a first-party navigation from Autobus.
        """
        self.require_config()
        return (
            f"{self._public_base()}/api/v1/whatsapp/embedded-signup/launch"
            f"?state={quote(state, safe='')}&go=1"
        )

    def embedded_signup_extras(self) -> Dict[str, Any]:
        extras: Dict[str, Any] = {
            "setup": {},
            "sessionInfoVersion": (
                os.getenv("META_WHATSAPP_SESSION_INFO_VERSION") or "3"
            ).strip(),
        }
        feature_type = (os.getenv("META_WHATSAPP_FEATURE_TYPE") or "").strip()
        if feature_type:
            extras["featureType"] = feature_type
        version = (os.getenv("META_WHATSAPP_ES_VERSION") or "").strip()
        if version:
            extras["version"] = version
        return extras

    def exchange_code(self, code: str) -> Dict[str, Any]:
        self.require_config()
        url = f"{self.graph_base}/oauth/access_token"
        payload = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code >= 400:
            # Some Meta setups reject redirect_uri on exchange for ES codes.
            payload_no_redirect = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "code": code,
            }
            resp = requests.get(url, params=payload_no_redirect, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("access_token"):
            raise RuntimeError(f"Token exchange returned no access_token: {data}")
        return data

    def _auth_headers(self, access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def resolve_waba_and_phone(
        self,
        access_token: str,
        waba_id: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        """Return (waba_id, phone_number_id, display_phone, verified_name)."""
        if waba_id and phone_number_id:
            display, name = self._phone_details(access_token, phone_number_id)
            return waba_id, phone_number_id, display, name

        if not waba_id:
            waba_id = self._discover_waba_id(access_token)
        if not waba_id:
            raise RuntimeError("Could not resolve WhatsApp Business Account ID")

        if not phone_number_id:
            phone_number_id, display, name = self._first_phone(access_token, waba_id)
        else:
            display, name = self._phone_details(access_token, phone_number_id)

        if not phone_number_id:
            raise RuntimeError("Could not resolve WhatsApp phone_number_id")
        return waba_id, phone_number_id, display, name

    def _discover_waba_id(self, access_token: str) -> Optional[str]:
        # Prefer debug_token granular scopes / shared WABA edge.
        try:
            app_token = f"{self.app_id}|{self.app_secret}"
            dbg = requests.get(
                f"{self.graph_base}/debug_token",
                params={"input_token": access_token, "access_token": app_token},
                timeout=30,
            )
            dbg.raise_for_status()
            data = dbg.json().get("data") or {}
            for scope in data.get("granular_scopes") or []:
                if scope.get("scope") in (
                    "whatsapp_business_management",
                    "whatsapp_business_messaging",
                ):
                    ids = scope.get("target_ids") or []
                    if ids:
                        return str(ids[0])
        except Exception as exc:
            logger.warning("[WA] debug_token WABA discovery failed: %s", exc)

        try:
            resp = requests.get(
                f"{self.graph_base}/me",
                params={
                    "fields": "whatsapp_business_accounts{id,name,phone_numbers{id,display_phone_number,verified_name}}",
                },
                headers=self._auth_headers(access_token),
                timeout=30,
            )
            if resp.status_code < 400:
                accounts = ((resp.json().get("whatsapp_business_accounts") or {}).get("data")) or []
                if accounts:
                    return str(accounts[0]["id"])
        except Exception as exc:
            logger.warning("[WA] /me WABA discovery failed: %s", exc)
        return None

    def _first_phone(
        self, access_token: str, waba_id: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        resp = requests.get(
            f"{self.graph_base}/{waba_id}/phone_numbers",
            params={"fields": "id,display_phone_number,verified_name"},
            headers=self._auth_headers(access_token),
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json().get("data") or []
        if not rows:
            return None, None, None
        row = rows[0]
        return (
            str(row.get("id")) if row.get("id") else None,
            row.get("display_phone_number"),
            row.get("verified_name"),
        )

    def _phone_details(
        self, access_token: str, phone_number_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = requests.get(
                f"{self.graph_base}/{phone_number_id}",
                params={"fields": "display_phone_number,verified_name"},
                headers=self._auth_headers(access_token),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("display_phone_number"), data.get("verified_name")
        except Exception as exc:
            logger.warning("[WA] phone details failed: %s", exc)
            return None, None

    def subscribe_webhooks(self, access_token: str, waba_id: str) -> bool:
        try:
            resp = requests.post(
                f"{self.graph_base}/{waba_id}/subscribed_apps",
                headers=self._auth_headers(access_token),
                timeout=30,
            )
            if resp.status_code >= 400:
                logger.error("[WA] subscribe_apps failed: %s %s", resp.status_code, resp.text)
                return False
            return bool(resp.json().get("success", True))
        except Exception as exc:
            logger.error("[WA] subscribe_apps error: %s", exc)
            return False

    def register_phone(self, access_token: str, phone_number_id: str) -> bool:
        try:
            resp = requests.post(
                f"{self.graph_base}/{phone_number_id}/register",
                headers=self._auth_headers(access_token),
                json={"messaging_product": "whatsapp", "pin": self.default_pin},
                timeout=30,
            )
            if resp.status_code >= 400:
                # Already registered is acceptable.
                body = (resp.text or "").lower()
                if "already" in body or resp.status_code in (400, 409):
                    logger.warning("[WA] register phone soft-fail: %s", resp.text[:300])
                    return True
                logger.error("[WA] register phone failed: %s %s", resp.status_code, resp.text)
                return False
            return bool(resp.json().get("success", True))
        except Exception as exc:
            logger.error("[WA] register phone error: %s", exc)
            return False

    @staticmethod
    def new_account_id() -> str:
        return f"wa_{uuid.uuid4().hex[:20]}"

    @staticmethod
    def encrypt_token(token: str) -> str:
        return encrypt_secret(token) or token

    @staticmethod
    def decrypt_token(token_encrypted: str) -> str:
        return decrypt_secret(token_encrypted) or token_encrypted
