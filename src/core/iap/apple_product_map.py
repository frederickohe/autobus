"""Map App Store product IDs to Autobus subscription plans.

Create matching auto-renewable subscriptions in App Store Connect under one
subscription group. Default product IDs (override with columns or APPLE_IAP_PRODUCT_MAP):

    autobus.{planslug}.monthly
    autobus.{planslug}.yearly

Example for plans named Basic, Standard, Enterprise:

    autobus.basic.monthly
    autobus.basic.yearly
    autobus.standard.monthly
    autobus.standard.yearly
    autobus.enterprise.monthly
    autobus.enterprise.yearly
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional, Tuple


def plan_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def product_prefix() -> str:
    return (os.getenv("APPLE_IAP_PRODUCT_PREFIX", "autobus") or "autobus").strip()


def apple_product_ids_for_plan(plan: Any) -> dict[str, str]:
    slug = plan_slug(getattr(plan, "name", "") or "")
    prefix = product_prefix()
    monthly = (getattr(plan, "apple_product_id_monthly", None) or "").strip()
    yearly = (getattr(plan, "apple_product_id_yearly", None) or "").strip()
    return {
        "monthly": monthly or f"{prefix}.{slug}.monthly",
        "annual": yearly or f"{prefix}.{slug}.yearly",
    }


def load_override_map() -> dict[str, Any]:
    raw = (os.getenv("APPLE_IAP_PRODUCT_MAP") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_plan_for_product(product_id: str, plans: list) -> Tuple[Optional[Any], Optional[str]]:
    """Return (plan, billing_period) for an App Store product ID."""
    pid = (product_id or "").strip()
    if not pid:
        return None, None

    overrides = load_override_map()
    override = overrides.get(pid)
    if isinstance(override, dict):
        plan_id = override.get("plan_id")
        period = (override.get("period") or "monthly").strip().lower()
        if period in ("year", "yearly", "annual", "annually"):
            period = "annual"
        elif period not in ("monthly", "annual"):
            period = "monthly"
        for plan in plans:
            if plan_id is not None and plan.id == plan_id:
                return plan, period
            if override.get("plan_name") and plan_slug(plan.name) == plan_slug(
                str(override.get("plan_name"))
            ):
                return plan, period

    for plan in plans:
        ids = apple_product_ids_for_plan(plan)
        for period, mapped in ids.items():
            if mapped == pid:
                return plan, period
    return None, None
