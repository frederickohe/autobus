"""Human-readable customer identity for owner-facing chat lists.

Conversations stay keyed by channel unique IDs (IGSID, WhatsApp wa_id) so
replies can be delivered. Owners should see username / phone instead.
"""

from __future__ import annotations

from typing import Optional, Tuple


def parse_conversation_user_id(
    conversation_user_id: Optional[str],
) -> Tuple[Optional[str], Optional[str], str]:
    """Split ``{merchant_id}:{channel}:{key}`` or ``{merchant_id}:{phone}``.

    Returns ``(merchant_id, channel, customer_key)``.
    ``channel`` is ``ig`` for Instagram; otherwise ``None``.
    """
    uid = (conversation_user_id or "").strip()
    if not uid:
        return None, None, ""
    if ":" not in uid:
        return None, None, uid

    merchant_id, _, rest = uid.partition(":")
    merchant_id = merchant_id.strip()
    rest = (rest or "").strip()
    if not merchant_id or not rest:
        return None, None, uid

    if rest.lower().startswith("ig:"):
        return merchant_id, "ig", rest[3:].strip()
    return merchant_id, None, rest


def customer_channel_key(conversation_user_id: Optional[str]) -> str:
    _, _, key = parse_conversation_user_id(conversation_user_id)
    return key


def is_instagram_conversation(conversation_user_id: Optional[str]) -> bool:
    _, channel, _ = parse_conversation_user_id(conversation_user_id)
    return channel == "ig"


def looks_like_phone(value: Optional[str]) -> bool:
    """True for typical phone numbers; false for social-platform unique IDs."""
    raw = (value or "").strip()
    if not raw or raw.lower().startswith("ig:"):
        return False
    if ":" in raw:
        return False
    digits = "".join(ch for ch in raw if ch.isdigit())
    # E.164 is at most 15 digits. Instagram IGSIDs are typically 16–17+.
    return 9 <= len(digits) <= 15


def normalize_username(value: Optional[str]) -> Optional[str]:
    cleaned = (value or "").strip().lstrip("@")
    return cleaned or None


def format_customer_label(
    *,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Optional[str]:
    """Owner-facing label: ``@username · phone`` when those values exist."""
    parts = []
    uname = normalize_username(username)
    if uname:
        parts.append(f"@{uname}")
    phone_clean = (phone or "").strip()
    if phone_clean and looks_like_phone(phone_clean):
        parts.append(phone_clean)
    if parts:
        return " · ".join(parts)
    name = (display_name or "").strip()
    return name or None
