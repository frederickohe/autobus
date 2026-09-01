"""Verify Google Play Billing consumables and grant Autobus credits."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from core.credits.credit_catalog import get_pack_by_store_product
from core.credits.service.credit_service import CreditService

logger = logging.getLogger(__name__)

_PLAY_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
_PLAY_API = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class GooglePlayIapError(Exception):
    pass


class GooglePlayIapService:
    def __init__(self, db: Session):
        self.db = db
        self.credits = CreditService(db)

    def _package_name(self, override: Optional[str] = None) -> str:
        return (
            (override or "").strip()
            or (os.getenv("GOOGLE_PLAY_PACKAGE_NAME") or "com.autobus.app").strip()
        )

    def _credentials(self):
        raw = (os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON") or "").strip()
        path = (
            (os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE") or "").strip()
            or (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
        )
        info = None
        if raw:
            try:
                info = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise GooglePlayIapError(
                    "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is not valid JSON"
                ) from exc
        elif path and os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                info = json.load(handle)
        if not isinstance(info, dict):
            raise GooglePlayIapError(
                "Google Play service account is not configured. "
                "Set GOOGLE_PLAY_SERVICE_ACCOUNT_JSON or GOOGLE_PLAY_SERVICE_ACCOUNT_FILE."
            )
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=[_PLAY_SCOPE],
        )

    def _access_token(self) -> str:
        creds = self._credentials()
        creds.refresh(Request())
        if not creds.token:
            raise GooglePlayIapError("Could not obtain a Google Play API access token")
        return str(creds.token)

    def _get_product_purchase(
        self,
        package_name: str,
        product_id: str,
        purchase_token: str,
    ) -> dict[str, Any]:
        url = (
            f"{_PLAY_API}/applications/{package_name}"
            f"/purchases/products/{product_id}/tokens/{purchase_token}"
        )
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    url,
                    headers={"Authorization": f"Bearer {self._access_token()}"},
                )
        except httpx.RequestError as exc:
            raise GooglePlayIapError("Google Play API is unreachable") from exc

        if response.status_code == 404:
            raise GooglePlayIapError("Google Play did not recognize this purchase")
        if response.status_code >= 400:
            logger.warning("Google Play verify failed: %s %s", response.status_code, response.text)
            raise GooglePlayIapError(
                "Google Play could not verify this purchase. Check Play Console API access."
            )
        data = response.json()
        return data if isinstance(data, dict) else {}

    def apply_purchase(
        self,
        user_id: str,
        purchase_token: str,
        product_id: str,
        package_name: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> dict[str, Any]:
        token = (purchase_token or "").strip()
        pid = (product_id or "").strip()
        if not token or not pid:
            return {
                "success": False,
                "message": "Google Play purchase is missing product or purchase token",
            }

        expected_package = self._package_name()
        pkg = self._package_name(package_name)
        if expected_package and pkg and pkg != expected_package:
            return {
                "success": False,
                "message": f"Package {pkg!r} does not match GOOGLE_PLAY_PACKAGE_NAME",
            }

        pack = get_pack_by_store_product(pid)
        if pack is None:
            return {
                "success": False,
                "message": (
                    f"No Autobus credit pack is mapped to Google Play product '{pid}'. "
                    "Create consumable products autobus.credits.20 / .50 / .150 / .400 "
                    "in Play Console."
                ),
                "product_id": pid,
            }

        try:
            payload = self._get_product_purchase(pkg, pid, token)
        except GooglePlayIapError as exc:
            return {"success": False, "message": str(exc), "product_id": pid}

        purchase_state = payload.get("purchaseState")
        # 0 = purchased, 1 = canceled, 2 = pending
        if purchase_state not in (0, "0", None):
            return {
                "success": False,
                "message": "This Google Play purchase is not completed",
                "product_id": pid,
            }

        txn = token
        result = self.credits.grant_pack(
            user_id=user_id,
            pack_id=pack["id"],
            provider="google_play",
            transaction_id=txn,
            product_id=pid,
            amount=float(pack["price_usd"]),
        )
        result["product_id"] = pid
        result["original_transaction_id"] = txn
        result["environment"] = "GooglePlay"
        result["plan_name"] = pack["name"]
        return result

    def handle_voided_purchase(self, purchase_token: str, reason: str = "Google Play voided") -> bool:
        token = (purchase_token or "").strip()
        if not token:
            return False
        return self.credits.refund_purchase("google_play", token, reason)
