import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.credits.credit_catalog import (
    FEATURE_CREDIT_COSTS,
    STARTER_CREDIT_GRANT,
    WALLET_CREDIT_TYPE,
    feature_cost,
    get_pack,
    packs_public,
)
from core.credits.model.credit_purchase import CreditPurchase
from core.credits.model.credit_types import CREDIT_TYPE_LABELS, ALL_CREDIT_TYPES
from core.credits.model.credit_usage_log import CreditUsageLog
from core.credits.model.user_credit_balance import UserCreditBalance
from core.user.model.User import User

logger = logging.getLogger(__name__)

_WALLET_PERIOD_START = datetime(1970, 1, 1, tzinfo=timezone.utc)
_WALLET_PERIOD_END = datetime(2099, 1, 1, tzinfo=timezone.utc)


class CreditService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_user_id(self, identifier: Optional[str]) -> Optional[str]:
        """Resolve internal user id from id, email, or phone."""
        if not identifier:
            return None
        user = (
            self.db.query(User)
            .filter(
                (User.id == identifier)
                | (User.email == identifier)
                | (User.phone == identifier)
            )
            .first()
        )
        return user.id if user else None

    def _ensure_internal_user_id(self, identifier: str) -> str:
        user_id = self.resolve_user_id(identifier)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user_id

    def _wallet_row(self, user_id: str) -> Optional[UserCreditBalance]:
        return (
            self.db.query(UserCreditBalance)
            .filter(
                UserCreditBalance.user_id == user_id,
                UserCreditBalance.credit_type == WALLET_CREDIT_TYPE,
            )
            .first()
        )

    def _legacy_category_rows(self, user_id: str) -> list[UserCreditBalance]:
        return (
            self.db.query(UserCreditBalance)
            .filter(
                UserCreditBalance.user_id == user_id,
                UserCreditBalance.credit_type != WALLET_CREDIT_TYPE,
            )
            .all()
        )

    def _legacy_wallet_value(self, user_id: str) -> float:
        total = 0.0
        for row in self._legacy_category_rows(user_id):
            unit = float(FEATURE_CREDIT_COSTS.get(row.credit_type, 0.0))
            total += max(0.0, float(row.remaining or 0)) * unit
        return total

    def _create_wallet(self, user_id: str, amount: float, allocated: Optional[float] = None) -> UserCreditBalance:
        value = max(0.0, float(amount))
        wallet = UserCreditBalance(
            user_id=user_id,
            subscription_id=None,
            credit_type=WALLET_CREDIT_TYPE,
            allocated=float(allocated if allocated is not None else value),
            remaining=value,
            period_start=_WALLET_PERIOD_START,
            period_end=_WALLET_PERIOD_END,
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def ensure_wallet(self, user_id: str) -> UserCreditBalance:
        """Lifetime wallet. Migrates leftover category credits, then grants starter."""
        user_id = self._ensure_internal_user_id(user_id)
        wallet = self._wallet_row(user_id)
        if wallet:
            return wallet

        converted = self._legacy_wallet_value(user_id)
        if converted > 0:
            return self._create_wallet(user_id, converted, allocated=converted)

        return self._create_wallet(
            user_id,
            STARTER_CREDIT_GRANT,
            allocated=STARTER_CREDIT_GRANT,
        )

    def grant_starter_credits(self, user_id: str) -> None:
        """Idempotent signup grant."""
        try:
            self.ensure_wallet(user_id)
        except Exception as exc:
            logger.warning("Starter credit grant failed for %s: %s", user_id, exc)

    def add_credits(
        self,
        user_id: str,
        amount: float,
        operation: str = "purchase",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserCreditBalance:
        user_id = self._ensure_internal_user_id(user_id)
        wallet = self.ensure_wallet(user_id)
        delta = max(0.0, float(amount))
        wallet.remaining = float(wallet.remaining) + delta
        wallet.allocated = float(wallet.allocated) + delta
        wallet.updated_at = datetime.now(timezone.utc)
        self.db.add(
            CreditUsageLog(
                user_id=user_id,
                credit_type=WALLET_CREDIT_TYPE,
                amount=-delta,
                operation=operation,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
        )
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def grant_pack(
        self,
        user_id: str,
        pack_id: str,
        provider: str,
        transaction_id: str,
        product_id: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Grant a catalog pack once per provider+transaction_id."""
        user_id = self._ensure_internal_user_id(user_id)
        pack = get_pack(pack_id)
        if not pack:
            return {"success": False, "message": f"Unknown credit pack '{pack_id}'"}

        txn = (transaction_id or "").strip()
        if not txn:
            return {"success": False, "message": "Missing purchase transaction id"}

        existing = (
            self.db.query(CreditPurchase)
            .filter(
                CreditPurchase.provider == provider,
                CreditPurchase.transaction_id == txn,
            )
            .first()
        )
        if existing:
            wallet = self.ensure_wallet(user_id)
            return {
                "success": True,
                "already_granted": True,
                "message": "Credits already applied for this purchase",
                "pack_id": existing.pack_id,
                "credits_granted": existing.credits,
                "wallet_remaining": wallet.remaining,
            }

        credits = float(pack["credits"])
        purchase = CreditPurchase(
            user_id=user_id,
            pack_id=pack["id"],
            credits=credits,
            provider=provider,
            transaction_id=txn,
            product_id=product_id,
            amount=amount,
            status="completed",
        )
        self.db.add(purchase)
        try:
            self.db.flush()
        except Exception:
            self.db.rollback()
            existing = (
                self.db.query(CreditPurchase)
                .filter(
                    CreditPurchase.provider == provider,
                    CreditPurchase.transaction_id == txn,
                )
                .first()
            )
            if existing:
                wallet = self.ensure_wallet(user_id)
                return {
                    "success": True,
                    "already_granted": True,
                    "message": "Credits already applied for this purchase",
                    "pack_id": existing.pack_id,
                    "credits_granted": existing.credits,
                    "wallet_remaining": wallet.remaining,
                }
            raise

        wallet = self.add_credits(
            user_id,
            credits,
            operation=f"{provider}_pack",
            metadata={"pack_id": pack["id"], "transaction_id": txn},
        )
        return {
            "success": True,
            "already_granted": False,
            "message": f"{int(credits) if credits == int(credits) else credits} credits added",
            "pack_id": pack["id"],
            "credits_granted": credits,
            "wallet_remaining": wallet.remaining,
        }

    def refund_purchase(self, provider: str, transaction_id: str, reason: str) -> bool:
        purchase = (
            self.db.query(CreditPurchase)
            .filter(
                CreditPurchase.provider == provider,
                CreditPurchase.transaction_id == transaction_id,
            )
            .first()
        )
        if not purchase or purchase.status == "refunded":
            return False
        wallet = self._wallet_row(purchase.user_id)
        clawback = min(float(purchase.credits), float(wallet.remaining) if wallet else 0.0)
        if wallet and clawback > 0:
            wallet.remaining = max(0.0, float(wallet.remaining) - clawback)
            wallet.updated_at = datetime.now(timezone.utc)
        purchase.status = "refunded"
        purchase.updated_at = datetime.now(timezone.utc)
        self.db.add(
            CreditUsageLog(
                user_id=purchase.user_id,
                credit_type=WALLET_CREDIT_TYPE,
                amount=clawback,
                operation="refund",
                metadata_json=json.dumps({"reason": reason, "transaction_id": transaction_id}),
            )
        )
        self.db.commit()
        return True

    def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        wallet = self.ensure_wallet(user_id)
        remaining = float(wallet.remaining)
        allocated = float(wallet.allocated)
        used = max(0.0, allocated - remaining)

        credits: Dict[str, Dict[str, Any]] = {}
        for credit_type in ALL_CREDIT_TYPES:
            unit = float(FEATURE_CREDIT_COSTS.get(credit_type, 1.0))
            actions = remaining / unit if unit > 0 else remaining
            credits[credit_type] = {
                "credit_type": credit_type,
                "label": CREDIT_TYPE_LABELS.get(credit_type, credit_type),
                "allocated": allocated / unit if unit > 0 else allocated,
                "remaining": actions,
                "used": max(0.0, (allocated - remaining) / unit) if unit > 0 else used,
                "wallet_cost": unit,
                "period_start": wallet.period_start.isoformat(),
                "period_end": wallet.period_end.isoformat(),
            }

        return {
            "user_id": user_id,
            "plan_id": None,
            "plan_name": "Credits",
            "has_active_subscription": True,
            "wallet": {
                "remaining": remaining,
                "allocated": allocated,
                "used": used,
            },
            "costs": dict(FEATURE_CREDIT_COSTS),
            "packs": packs_public(),
            "credits": credits,
        }

    def get_remaining(self, user_id: str, credit_type: str) -> float:
        wallet = self.ensure_wallet(user_id)
        if credit_type == WALLET_CREDIT_TYPE:
            return float(wallet.remaining)
        unit = feature_cost(credit_type, 1.0)
        if unit <= 0:
            return float("inf")
        return float(wallet.remaining) / unit

    def has_credits(self, user_id: str, credit_type: str, amount: float = 1.0) -> bool:
        needed = feature_cost(credit_type, amount)
        if needed <= 0:
            return True
        wallet = self.ensure_wallet(user_id)
        return float(wallet.remaining) >= needed

    def check_and_deduct(
        self,
        user_id: str,
        credit_type: str,
        amount: float = 1.0,
        operation: str = "usage",
        metadata: Optional[Dict[str, Any]] = None,
        raise_on_insufficient: bool = True,
    ) -> bool:
        user_id = self._ensure_internal_user_id(user_id)
        needed = feature_cost(credit_type, amount)
        wallet = self.ensure_wallet(user_id)

        if needed > 0 and float(wallet.remaining) < needed:
            if raise_on_insufficient:
                label = CREDIT_TYPE_LABELS.get(credit_type, credit_type)
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "message": f"Insufficient credits for {label}. Buy more credits to continue.",
                        "credit_type": credit_type,
                        "remaining": wallet.remaining,
                        "required": needed,
                    },
                )
            return False

        if needed > 0:
            wallet.remaining = max(0.0, float(wallet.remaining) - needed)
            wallet.updated_at = datetime.now(timezone.utc)

        log_meta = dict(metadata or {})
        log_meta["feature"] = credit_type
        log_meta["wallet_cost"] = needed
        self.db.add(
            CreditUsageLog(
                user_id=user_id,
                credit_type=credit_type,
                amount=needed,
                operation=operation,
                metadata_json=json.dumps(log_meta),
            )
        )
        self.db.commit()
        return True

    def require_credits(
        self,
        user_id: str,
        credit_type: str,
        amount: float = 1.0,
        operation: str = "usage",
    ) -> None:
        self.check_and_deduct(
            user_id=user_id,
            credit_type=credit_type,
            amount=amount,
            operation=operation,
            raise_on_insufficient=True,
        )

    # Legacy no-ops so older callers / startup hooks stay safe.
    def get_plan_allocations(self, plan) -> Dict[str, float]:
        return {}

    def sync_plan_credit_allocations(self) -> int:
        return 0

    def initialize_credits_for_subscription(self, user_id: str, subscription=None) -> None:
        self.grant_starter_credits(user_id)
