"""Apply verified App Store consumable transactions as Autobus credits."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from core.credits.credit_catalog import get_pack_by_apple_product
from core.credits.service.credit_service import CreditService
from core.iap.apple_jws import AppleJwsError, decode_signed_data

_REFUND_NOTIFICATIONS = {
    "EXPIRED",
    "GRACE_PERIOD_EXPIRED",
    "REFUND",
    "REVOKE",
    "REFUND_REVERSED",
}


class AppleIapService:
    def __init__(self, db: Session):
        self.db = db
        self.credits = CreditService(db)

    def _expected_bundle_id(self) -> str:
        return (os.getenv("APPLE_BUNDLE_ID") or "").strip()

    def decode_transaction(self, signed_transaction: str) -> dict[str, Any]:
        payload = decode_signed_data(signed_transaction)
        bundle_id = str(payload.get("bundleId") or "")
        expected = self._expected_bundle_id()
        if expected and bundle_id and bundle_id != expected:
            raise AppleJwsError(
                f"Transaction bundleId {bundle_id!r} does not match APPLE_BUNDLE_ID"
            )
        return payload

    def apply_signed_transaction(
        self,
        user_id: str,
        signed_transaction: str,
        expected_plan_id: int | None = None,
        expected_billing_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self.decode_transaction(signed_transaction)
        product_id = str(payload.get("productId") or "")
        original_transaction_id = str(payload.get("originalTransactionId") or "")
        transaction_id = str(payload.get("transactionId") or original_transaction_id)
        environment = str(payload.get("environment") or "")

        if not product_id or not transaction_id:
            return {
                "success": False,
                "message": "App Store transaction is missing product or transaction id",
            }

        if payload.get("revocationDate"):
            self.credits.refund_purchase(
                "apple_iap",
                transaction_id,
                "App Store revocation",
            )
            return {
                "success": False,
                "message": "This App Store purchase was revoked or refunded",
                "product_id": product_id,
                "original_transaction_id": original_transaction_id,
                "environment": environment,
            }

        pack = get_pack_by_apple_product(product_id)
        if pack is None:
            return {
                "success": False,
                "message": (
                    f"No Autobus credit pack is mapped to App Store product '{product_id}'. "
                    "Create consumable products autobus.credits.20.v4 / .50.v4 / .150.v5 / .400.v4 "
                    "in App Store Connect."
                ),
                "product_id": product_id,
            }

        amount = float(pack["price_usd"])
        try:
            raw_price = payload.get("price")
            if raw_price is not None:
                amount = float(raw_price) / 1000.0
        except (TypeError, ValueError):
            pass

        result = self.credits.grant_pack(
            user_id=user_id,
            pack_id=pack["id"],
            provider="apple_iap",
            transaction_id=transaction_id,
            product_id=product_id,
            amount=amount,
        )
        result["product_id"] = product_id
        result["original_transaction_id"] = original_transaction_id
        result["environment"] = environment
        result["plan_id"] = None
        result["plan_name"] = pack["name"]
        return result

    def handle_server_notification(self, signed_payload: str) -> dict[str, Any]:
        envelope = decode_signed_data(signed_payload)
        notification_type = str(envelope.get("notificationType") or "").upper()
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        signed_txn = data.get("signedTransactionInfo") if isinstance(data, dict) else None
        if not signed_txn:
            return {
                "success": True,
                "message": f"Ignored App Store notification {notification_type} without transaction",
            }

        payload = self.decode_transaction(signed_txn)
        transaction_id = str(payload.get("transactionId") or payload.get("originalTransactionId") or "")
        product_id = str(payload.get("productId") or "")

        if notification_type in _REFUND_NOTIFICATIONS:
            self.credits.refund_purchase(
                "apple_iap",
                transaction_id,
                f"App Store notification {notification_type}",
            )
            return {
                "success": True,
                "message": f"Processed {notification_type}",
                "original_transaction_id": transaction_id,
                "product_id": product_id,
            }

        return {
            "success": True,
            "message": f"Ignored App Store notification {notification_type}",
            "original_transaction_id": transaction_id,
            "product_id": product_id,
        }
