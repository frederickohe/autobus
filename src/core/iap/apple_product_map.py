"""Map App Store consumable product IDs to Autobus credit packs."""

from __future__ import annotations

from typing import Any, Optional

from core.credits.credit_catalog import CREDIT_PACKS, apple_product_ids, get_pack_by_apple_product


def all_apple_credit_product_ids() -> list[str]:
    return apple_product_ids()


def resolve_pack_for_product(product_id: str) -> Optional[dict[str, Any]]:
    return get_pack_by_apple_product(product_id)


def credit_pack_catalog() -> list[dict[str, Any]]:
    return list(CREDIT_PACKS)


def apple_product_ids_for_plan(plan: Any) -> dict[str, str]:
    """Deprecated subscription mapping. Credit packs are the IAP catalog now."""
    return {"monthly": "", "annual": ""}
