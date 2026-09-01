"""Unified credit wallet catalog.

1 Autobus credit = $0.20 USD list value so video generation is 4 credits
at the $0.80 customer charge. Feature costs follow the internal rate card.

iOS sells these packs as App Store consumables. Android and web sell them via
Paystack. Catalog prices are USD so both platforms quote the same dollar
amount; Paystack charges the live GHS equivalent at checkout.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# List value used to convert USD charges into credits.
CREDIT_USD_VALUE = 0.20

# New accounts receive this so App Review and first-run users can try features.
STARTER_CREDIT_GRANT = 15.0

# Credits deducted per 1.0 unit of the feature type.
# storage_mb amount is megabytes uploaded; server requests are not metered.
FEATURE_CREDIT_COSTS: Dict[str, float] = {
    "llm": 0.05,  # $0.01 per chat
    "image_gen": 1.25,  # $0.25 per image
    "video_gen": 4.0,  # $0.80 per video
    "email": 0.2,  # $0.04 per email
    "sms": 0.01,  # $0.002 per SMS
    "storage_mb": 0.02,  # 50 MB ≈ 1 credit ≈ $0.20
    "server": 0.0,
}

CREDIT_PACKS: List[Dict[str, Any]] = [
    {
        "id": "starter",
        "name": "Starter",
        "credits": 20.0,
        "price_usd": 4.99,
        "apple_product_id": "autobus.credits.20.v4",
        "google_play_product_id": "autobus.credits.20",
        "description": "20 credits",
        "details": "Add 20 credits to your wallet. That's about 5 videos or 16 images, plus AI chats, email and SMS. Credits stay until you use them.",
    },
    {
        "id": "plus",
        "name": "Plus",
        "credits": 50.0,
        "price_usd": 12.99,
        "apple_product_id": "autobus.credits.50.v4",
        "google_play_product_id": "autobus.credits.50",
        "description": "50 credits",
        "details": "Add 50 credits for weekly marketing. Roughly 12 videos or 40 images, with plenty left for customer chats and messages.",
    },
    {
        "id": "pro",
        "name": "Pro",
        "credits": 150.0,
        "price_usd": 34.99,
        "apple_product_id": "autobus.credits.150.v5",
        "google_play_product_id": "autobus.credits.150",
        "description": "150 credits",
        "details": "Add 150 credits for campaigns and a busy inbox. About 37 videos or 120 images, or a mix of generation, chats and messaging.",
    },
    {
        "id": "business",
        "name": "Business",
        "credits": 400.0,
        "price_usd": 79.99,
        "apple_product_id": "autobus.credits.400.v4",
        "google_play_product_id": "autobus.credits.400",
        "description": "400 credits",
        "details": "Add 400 credits at the best rate per credit. Built for daily use: videos, product photos, AI chats, email and SMS.",
    },
]

WALLET_CREDIT_TYPE = "wallet"


def feature_cost(credit_type: str, amount: float = 1.0) -> float:
    unit = float(FEATURE_CREDIT_COSTS.get(credit_type, 1.0))
    return max(0.0, unit * float(amount))


def get_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    key = (pack_id or "").strip().lower()
    for pack in CREDIT_PACKS:
        if pack["id"] == key:
            return pack
    return None


def get_pack_by_apple_product(product_id: str) -> Optional[Dict[str, Any]]:
    return get_pack_by_store_product(product_id)


def get_pack_by_store_product(product_id: str) -> Optional[Dict[str, Any]]:
    pid = (product_id or "").strip()
    for pack in CREDIT_PACKS:
        if pack["apple_product_id"] == pid or pack.get("google_play_product_id") == pid:
            return pack
    return None


def apple_product_ids() -> List[str]:
    return [str(p["apple_product_id"]) for p in CREDIT_PACKS]


def store_product_ids() -> List[str]:
    ids: List[str] = []
    for pack in CREDIT_PACKS:
        for key in ("apple_product_id", "google_play_product_id"):
            value = str(pack.get(key) or "")
            if value and value not in ids:
                ids.append(value)
    return ids


def packs_public() -> List[Dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "credits": p["credits"],
            "price_usd": p["price_usd"],
            "paystack_amount": 0,
            "apple_product_id": p["apple_product_id"],
            "google_play_product_id": p.get("google_play_product_id") or p["apple_product_id"],
            "description": p["description"],
            "details": p.get("details") or p["description"],
        }
        for p in CREDIT_PACKS
    ]
