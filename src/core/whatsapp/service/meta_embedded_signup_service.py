"""Meta WhatsApp Embedded Signup / Business App onboarding helpers."""

from __future__ import annotations

import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests

from utilities.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


class MetaWhatsAppOAuthState:
    """In-memory CSRF state for Meta WhatsApp onboarding (Redis preferred later)."""

    _states: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create(cls, user_id: str) -> str:
        state = secrets.token_urlsafe(32)
        cls._states[state] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
        }
        return state

    @classmethod
    def validate(cls, state: str) -> Optional[str]:
        data = cls._states.get(state)
        if not data:
            return None
        if datetime.utcnow() > data["expires_at"]:
            cls._states.pop(state, None)
            return None
        cls._states.pop(state, None)
        return data["user_id"]


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
        self.require_config()
        extras = {
            "version": "v4",
            "sessionInfoVersion": "3",
            "featureType": "whatsapp_business_app_onboarding",
        }
        params = {
            "app_id": self.app_id,
            "config_id": self.config_id,
            "extras": json.dumps(extras, separators=(",", ":")),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return (
            "https://business.facebook.com/messaging/whatsapp/onboard/?"
            + urlencode(params)
        )

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
