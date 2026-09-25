"""Partition an embed session by the caller's sub-business, such as a store under Shopify."""
from typing import Any, Iterable, List, Optional


def session_user_id(merchant_id: str, customer_id: str, sub_business_id: str = "") -> str:
    sub = (sub_business_id or "").strip()
    if sub:
        return f"{merchant_id}:sb:{sub}:{customer_id}"
    return f"{merchant_id}:{customer_id}"


def sub_business_from_session(user_id: str) -> str:
    if not user_id or ":sb:" not in user_id:
        return ""
    _, _, rest = user_id.partition(":sb:")
    sub, sep, _customer = rest.partition(":")
    if not sep:
        return ""
    return sub.strip()


def for_sub_business(products: Iterable[Any], sub_business_id: Optional[str]) -> List[Any]:
    wanted = (sub_business_id or "").strip()
    kept = []
    for product in products or []:
        stored = (getattr(product, "sub_business_id", None) or "").strip()
        if stored == wanted:
            kept.append(product)
    return kept
