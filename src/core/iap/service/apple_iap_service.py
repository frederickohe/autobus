"""Apply verified App Store transactions to Autobus subscriptions."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from core.iap.apple_jws import AppleJwsError, decode_signed_data, millis_to_datetime
from core.iap.apple_product_map import resolve_plan_for_product
from core.subscription.model.user_subscription import SubscriptionStatus, UserSubscription
from core.subscription.service.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

_EXPIRE_NOTIFICATIONS = {
    "EXPIRED",
    "GRACE_PERIOD_EXPIRED",
    "REFUND",
    "REVOKE",
}

_APPLY_NOTIFICATIONS = {
    "SUBSCRIBED",
    "DID_RENEW",
    "DID_CHANGE_RENEWAL_PREF",
    "OFFER_REDEEMED",
    "RENEWAL_EXTENDED",
    "RENEWAL_DATE_UPDATED",
}


class AppleIapService:
    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionService(db)

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
        expected_plan_id: Optional[int] = None,
        expected_billing_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload = self.decode_transaction(signed_transaction)
        product_id = str(payload.get("productId") or "")
        original_transaction_id = str(payload.get("originalTransactionId") or "")
        transaction_id = str(payload.get("transactionId") or original_transaction_id)
        environment = str(payload.get("environment") or "")
        expires_at = millis_to_datetime(payload.get("expiresDate"))
        purchase_date = millis_to_datetime(payload.get("purchaseDate"))

        if not product_id or not original_transaction_id:
            return {
                "success": False,
                "message": "App Store transaction is missing product or original transaction id",
            }

        revocation = payload.get("revocationDate")
        if revocation:
            expired = self.expire_by_original_transaction_id(
                original_transaction_id,
                reason="App Store revocation",
            )
            if expired:
                return {
                    "success": False,
                    "message": "This App Store purchase was revoked or refunded",
                    "product_id": product_id,
                    "original_transaction_id": original_transaction_id,
                    "environment": environment,
                }

        plans = self.subscriptions.get_all_plans()
        plan, period = resolve_plan_for_product(product_id, plans)
        if plan is None:
            return {
                "success": False,
                "message": (
                    f"No Autobus plan is mapped to App Store product '{product_id}'. "
                    "Create the product in App Store Connect and match APPLE_IAP_PRODUCT_PREFIX."
                ),
                "product_id": product_id,
            }

        if expected_plan_id and plan.id != expected_plan_id:
            return {
                "success": False,
                "message": "The App Store product does not match the selected plan",
                "product_id": product_id,
                "plan_id": plan.id,
            }

        if expected_billing_id:
            expected = expected_billing_id.strip().lower()
            if expected in ("year", "yearly", "annually"):
                expected = "annual"
            if period and expected and period != expected:
                return {
                    "success": False,
                    "message": "The App Store product does not match the selected billing period",
                    "product_id": product_id,
                }

        if expires_at is None:
            if period == "annual":
                expires_at = (purchase_date or datetime.now(timezone.utc)) + timedelta(days=365)
            else:
                expires_at = (purchase_date or datetime.now(timezone.utc)) + timedelta(days=30)

        amount = plan.price
        try:
            raw_price = payload.get("price")
            if raw_price is not None:
                amount = float(raw_price) / 1000.0
        except (TypeError, ValueError):
            pass

        result = self.subscriptions.apply_apple_subscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_reference=f"apple:{transaction_id}",
            expires_at=expires_at,
            amount_paid=amount,
            apple_original_transaction_id=original_transaction_id,
            apple_product_id=product_id,
        )
        result["product_id"] = product_id
        result["original_transaction_id"] = original_transaction_id
        result["environment"] = environment
        result["plan_id"] = plan.id
        return result

    def expire_by_original_transaction_id(
        self,
        original_transaction_id: str,
        reason: str,
    ) -> bool:
        if not original_transaction_id:
            return False
        rows = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.apple_original_transaction_id == original_transaction_id,
            )
            .all()
        )
        if not rows:
            return False
        now = datetime.now(timezone.utc)
        changed = False
        for row in rows:
            if row.status == SubscriptionStatus.ACTIVE:
                row.status = SubscriptionStatus.EXPIRED
                row.cancelled_at = now
                row.updated_at = now
                row.notes = (row.notes or "") + f" | {reason}"
                changed = True
        if changed:
            self.db.commit()
        return changed

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
        original_transaction_id = str(payload.get("originalTransactionId") or "")
        product_id = str(payload.get("productId") or "")

        if notification_type in _EXPIRE_NOTIFICATIONS:
            self.expire_by_original_transaction_id(
                original_transaction_id,
                reason=f"App Store notification {notification_type}",
            )
            return {
                "success": True,
                "message": f"Processed {notification_type}",
                "original_transaction_id": original_transaction_id,
                "product_id": product_id,
            }

        if notification_type in _APPLY_NOTIFICATIONS or not notification_type:
            existing = (
                self.db.query(UserSubscription)
                .filter(
                    UserSubscription.apple_original_transaction_id == original_transaction_id,
                )
                .order_by(UserSubscription.created_at.desc())
                .first()
            )
            if not existing:
                return {
                    "success": True,
                    "message": (
                        f"Received {notification_type or 'transaction'} for an unknown "
                        "originalTransactionId; waiting for the app to verify"
                    ),
                    "original_transaction_id": original_transaction_id,
                }
            result = self.apply_signed_transaction(
                user_id=existing.user_id,
                signed_transaction=signed_txn,
            )
            result["notification_type"] = notification_type
            return result

        return {
            "success": True,
            "message": f"Ignored App Store notification {notification_type}",
            "original_transaction_id": original_transaction_id,
        }
