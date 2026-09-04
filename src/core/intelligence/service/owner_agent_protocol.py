"""Pure helpers for the owner agent turn protocol (no LLM / DB imports)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

WRITE_TOOLS = frozenset(
    {
        "create_product",
        "update_product",
        "create_customer",
        "send_customer_sms",
        "send_customer_email",
    }
)

CONTROL_TOOLS = frozenset({"ask_user"})

CONFIRM_TITLES = {
    "create_product": "Add this product to your catalog?",
    "update_product": "Update this product?",
    "create_customer": "Save this customer?",
    "send_customer_sms": "Send this SMS?",
    "send_customer_email": "Send this email?",
}

_ASK_ACCEPT = {
    "image": ["image/jpeg", "image/png", "image/webp", "image/gif"],
    "video": ["video/mp4", "video/quicktime", "video/webm"],
    "file": [
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
}


def confirm_title(tool: str) -> str:
    return CONFIRM_TITLES.get(tool, "Go ahead with this?")


def confirm_summary(tool: str, args: Dict[str, Any]) -> str:
    args = args or {}
    if tool == "create_product":
        name = str(args.get("name") or "this product").strip()
        price = args.get("price")
        stock = args.get("number_in_stock")
        bits = [name]
        if price is not None:
            bits.append(f"price {price}")
        if stock is not None:
            bits.append(f"stock {stock}")
        media = len(args.get("photos") or []) + len(args.get("videos") or [])
        if media:
            bits.append(f"{media} media file{'s' if media != 1 else ''}")
        return "Add " + ", ".join(bits) + "."
    if tool == "update_product":
        return f"Update product {args.get('product_id') or ''} with the details I prepared.".strip()
    if tool == "create_customer":
        name = str(args.get("name") or "this customer").strip()
        number = str(args.get("customer_number") or "").strip()
        extra = f" ({number})" if number else ""
        return f"Save {name}{extra} to your customer list."
    if tool == "send_customer_sms":
        ids = args.get("customer_ids") or []
        body = str(args.get("message") or "").strip()
        preview = body if len(body) <= 120 else body[:117] + "..."
        n = len(ids) if isinstance(ids, list) else 1
        return f"SMS {n} customer{'s' if n != 1 else ''}: {preview}"
    if tool == "send_customer_email":
        subject = str(args.get("subject") or "this email").strip()
        ids = args.get("customer_ids") or []
        n = len(ids) if isinstance(ids, list) else 1
        return f"Email {n} customer{'s' if n != 1 else ''} — subject: {subject}"
    return json.dumps(args, default=str)[:400]


def ask_accept_for(kind: str) -> List[str]:
    return list(_ASK_ACCEPT.get((kind or "").strip().lower(), []))


def compose_user_content(message: Optional[str], attachments: Optional[List[Any]]) -> str:
    parts: List[str] = []
    text = (message or "").strip()
    if text:
        parts.append(text)
    for item in attachments or []:
        kind = str(_field(item, "kind") or "file").strip() or "file"
        url = str(_field(item, "url") or "").strip()
        name = str(_field(item, "name") or "").strip()
        label = url or name or kind
        parts.append(f"[attached {kind}] {label}")
    return "\n".join(parts).strip() or "(empty)"


def _field(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def parse_control_payload(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    blob = match.group(1) if match else text
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(blob[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    kind = str(data.get("type") or "").strip().lower()
    if kind in {"reply", "ask_input", "ask_user", "confirm", "call_tool"}:
        return data
    return None
