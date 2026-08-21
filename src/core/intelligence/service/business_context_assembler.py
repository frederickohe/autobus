"""Assemble live, tenant-scoped business facts for the owner's My AI copilot."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from core.conversationmanager.service.conversation_list_service import ConversationListService
from core.orders.service.order_service import OrderService
from core.product.service.product_service import ProductService
from core.rag.conversation_vector_client import ConversationVectorClient
from core.rag.tenant import resolve_effective_rag_tenant_id
from core.user.model.User import User

logger = logging.getLogger(__name__)

_KNOWLEDGE_SOURCES = ["document", "website"]
_RAG_HIT_LIMIT = 12
_RAG_SCORE_THRESHOLD = 0.35
_RAG_CHAR_BUDGET = 3200
_PRODUCT_CHAR_BUDGET = 1800
_PRODUCT_LIMIT = 24
_ORDER_LIMIT = 10
_INBOX_LIMIT = 8
_EXCERPT_MAX = 420
_OWNER_AI_PREFIX = "owner_ai:"

_GREETING_EXACT = {
    "hello",
    "hi",
    "hey",
    "hiya",
    "yo",
    "hola",
    "good morning",
    "good afternoon",
    "good evening",
    "hey there",
    "hi there",
    "hello there",
}

_SNAPSHOT_HINTS = (
    "overview",
    "status quo",
    "how's my business",
    "how is my business",
    "hows my business",
    "how's business",
    "how is business",
    "summary",
    "dashboard",
    "what's going on",
    "whats going on",
    "what is going on",
    "catch me up",
    "status",
    "snapshot",
)

_ORDER_HINTS = (
    "order",
    "orders",
    "sale",
    "sales",
    "invoice",
    "payment",
    "paid",
    "unpaid",
    "pending",
    "fulfill",
    "ship",
    "delivery",
    "delivered",
    "refund",
    "customer bought",
    "who ordered",
)

_INBOX_HINTS = (
    "inbox",
    "message",
    "messages",
    "messaging",
    "chat",
    "chats",
    "conversation",
    "conversations",
    "intervention",
    "handover",
    "waiting",
    "unread",
    "customer said",
    "customers waiting",
    "support",
)

_PRODUCT_HINTS = (
    "product",
    "products",
    "catalog",
    "catalogue",
    "inventory",
    "stock",
    "price",
    "prices",
    "sell",
    "selling",
    "sku",
    "item",
    "items",
)


@dataclass
class BusinessContext:
    profile: Optional[str] = None
    knowledge: Optional[str] = None
    products: Optional[str] = None
    orders: Optional[str] = None
    inbox: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    snapshot: Dict[str, Any] = field(default_factory=dict)

    def as_prompt_block(self) -> str:
        sections: List[str] = []
        if self.profile:
            sections.extend(["## Business profile", self.profile])
        if self.products:
            sections.extend(["", "## Product catalog (live)", self.products])
        if self.orders:
            sections.extend(["", "## Orders (live)", self.orders])
        if self.inbox:
            sections.extend(["", "## Inbox and conversations (live)", self.inbox])
        if self.knowledge:
            sections.extend(
                [
                    "",
                    "## Indexed knowledge (uploaded files and websites)",
                    self.knowledge,
                ]
            )
        if not sections:
            return (
                "No business profile, products, orders, inbox, or indexed knowledge "
                "is available yet."
            )
        return "\n".join(sections).strip()


class BusinessContextAssembler:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._rag = ConversationVectorClient()

    def assemble(self, user: User, query: str) -> BusinessContext:
        q = (query or "").strip()
        snapshot_mode = _wants_snapshot(q)
        include_orders = snapshot_mode or _mentions(_ORDER_HINTS, q)
        include_inbox = snapshot_mode or _mentions(_INBOX_HINTS, q)

        ctx = BusinessContext()
        ctx.profile = _format_business_profile(user)
        if ctx.profile:
            ctx.sources.append("profile")

        products, product_count = self._format_products(user.id, q)
        ctx.products = products
        if ctx.products:
            ctx.sources.append("products")

        knowledge = self._format_knowledge(user, q)
        ctx.knowledge = knowledge
        if ctx.knowledge:
            ctx.sources.append("knowledge")

        order_count_active = 0
        if include_orders:
            orders, order_count_active = self._format_orders(user.id, q)
            ctx.orders = orders
            if ctx.orders:
                ctx.sources.append("orders")

        inbox_waiting = 0
        if include_inbox:
            inbox, inbox_waiting = self._format_inbox(user.id)
            ctx.inbox = inbox
            if ctx.inbox:
                ctx.sources.append("inbox")

        ctx.snapshot = {
            "business_name": _business_display_name(user),
            "owner_name": (user.fullname or "").strip() or None,
            "product_count": product_count,
            "active_order_count": order_count_active,
            "inbox_waiting_count": inbox_waiting,
            "has_knowledge": bool(ctx.knowledge),
        }
        return ctx

    def _format_products(self, user_id: str, query: str) -> tuple[Optional[str], int]:
        try:
            products = ProductService(self.db).get_products_by_user(
                str(user_id), skip=0, limit=_PRODUCT_LIMIT
            )
        except Exception as e:
            logger.warning("[MY_AI] Product lookup failed: %s", e, exc_info=True)
            return None, 0
        if not products:
            return "No products in the catalog yet.", 0

        needle = (query or "").strip().lower()
        ranked = list(products)
        if needle and _mentions(_PRODUCT_HINTS, query):
            ranked.sort(
                key=lambda p: (
                    0
                    if needle and needle in _clean(getattr(p, "name", "")).lower()
                    else 1
                )
            )

        lines: List[str] = []
        used = 0
        for product in ranked:
            name = _clean(getattr(product, "name", None))
            if not name:
                continue
            bits = [f"- {name}"]
            price = getattr(product, "price", None)
            if price is not None:
                bits.append(f"price={price}")
            category = _clean(getattr(product, "category", None))
            if category:
                bits.append(f"category={category}")
            stock = getattr(product, "number_in_stock", None)
            if stock is not None:
                bits.append(f"stock={stock}")
            desc = _clean(getattr(product, "description", None), max_len=140)
            line = " | ".join(bits)
            if desc:
                line += f" — {desc}"
            if used + len(line) + 1 > _PRODUCT_CHAR_BUDGET:
                break
            lines.append(line)
            used += len(line) + 1
        if not lines:
            return "No products in the catalog yet.", 0
        return "\n".join(lines), len(products)

    def _format_orders(self, user_id: str, query: str) -> tuple[Optional[str], int]:
        service = OrderService(self.db)
        active: List[Any] = []
        try:
            active = service.get_admin_active_orders(str(user_id), skip=0, limit=_ORDER_LIMIT)
        except Exception as e:
            logger.warning("[MY_AI] Active order lookup failed: %s", e, exc_info=True)

        extra: List[Any] = []
        token = _possible_order_number(query)
        if token:
            try:
                found = service.get_order_by_number(token)
                if found and str(getattr(found, "user_id", "") or "") == str(user_id):
                    extra.append(found)
            except Exception as e:
                logger.warning("[MY_AI] Order-number lookup failed: %s", e, exc_info=True)

        completed: List[Any] = []
        try:
            completed = service.get_admin_completed_orders(
                str(user_id), skip=0, limit=4
            )
        except Exception as e:
            logger.warning("[MY_AI] Completed order lookup failed: %s", e, exc_info=True)

        seen: Set[str] = set()
        lines: List[str] = []
        for order in extra + active + completed:
            oid = str(getattr(order, "order_id", "") or getattr(order, "order_number", "") or "")
            if oid and oid in seen:
                continue
            if oid:
                seen.add(oid)
            line = _format_order_line(order)
            if line:
                lines.append(line)

        if not lines:
            return "No orders on file yet.", 0
        header = f"Open / needing attention: {len(active)}."
        return header + "\n" + "\n".join(lines[:_ORDER_LIMIT]), len(active)

    def _format_inbox(self, user_id: str) -> tuple[Optional[str], int]:
        try:
            completed, waiting = ConversationListService(
                self.db
            ).list_grouped_conversations_for_user(str(user_id), skip=0, limit=40)
        except Exception as e:
            logger.warning("[MY_AI] Inbox lookup failed: %s", e, exc_info=True)
            return None, 0

        waiting_rows = [s for s in waiting if not _is_owner_ai_session(s.user_id)]
        recent_rows = [s for s in completed if not _is_owner_ai_session(s.user_id)][:_INBOX_LIMIT]

        lines: List[str] = [
            f"Conversations waiting on a human: {len(waiting_rows)}.",
            f"Other recent conversations: {len(recent_rows)} shown of latest list.",
        ]
        for summary in waiting_rows[:_INBOX_LIMIT]:
            lines.append(_format_inbox_line(summary, waiting=True))
        for summary in recent_rows:
            lines.append(_format_inbox_line(summary, waiting=False))

        if len(waiting_rows) == 0 and len(recent_rows) == 0:
            return "No customer conversations in the inbox yet.", 0
        return "\n".join(lines), len(waiting_rows)

    def _format_knowledge(self, user: User, query: str) -> Optional[str]:
        if not self._rag.enabled():
            logger.warning("[MY_AI] RAG_SERVICE_URL not configured; skipping indexed knowledge")
            return None
        user_data = {
            "db_user_id": user.id,
            "company": user.company,
            "user_id": user.phone,
        }
        tenant_id = resolve_effective_rag_tenant_id(
            user_data, fallback_db_user_id=user.id
        )
        if not tenant_id:
            return None
        search_query = (query or "").strip() or (user.company or "business")
        try:
            hits = self._rag.search(
                tenant_id=tenant_id,
                query=search_query,
                limit=_RAG_HIT_LIMIT,
                score_threshold=_RAG_SCORE_THRESHOLD,
                sources=_KNOWLEDGE_SOURCES,
            )
        except Exception as e:
            logger.warning("[MY_AI] knowledge search failed: %s", e, exc_info=True)
            return None
        excerpts = _excerpts_from_hits(hits or [])
        if not excerpts:
            return None
        return "\n".join(excerpts)


def owner_conversation_key(user_id: str) -> str:
    return f"{_OWNER_AI_PREFIX}{user_id}"


def is_owner_greeting(message: str) -> bool:
    t = _normalize_query(message)
    if t in _GREETING_EXACT:
        return True
    return t.startswith("hello") and len(t.split()) <= 3


def _wants_snapshot(query: str) -> bool:
    t = _normalize_query(query)
    if is_owner_greeting(query):
        return True
    return any(hint in t for hint in _SNAPSHOT_HINTS)


def _mentions(hints: tuple, query: str) -> bool:
    t = _normalize_query(query)
    if not t:
        return False
    return any(h in t for h in hints)


def _normalize_query(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("’", "'").replace("‘", "'")
    t = re.sub(r"[.!?]+$", "", t).strip()
    return t


def _possible_order_number(query: str) -> Optional[str]:
    raw = (query or "").strip()
    if not raw:
        return None
    match = re.search(r"\b([A-Za-z]{1,6}-?\d{3,})\b", raw)
    if match:
        return match.group(1)
    match = re.search(r"\b(?:order|#)\s*([A-Za-z0-9-]{4,})\b", raw, re.I)
    if match:
        return match.group(1)
    return None


def _is_owner_ai_session(user_id: Optional[str]) -> bool:
    return (user_id or "").startswith(_OWNER_AI_PREFIX)


def _business_display_name(user: User) -> str:
    for value in (user.company, user.organization_workplace, user.fullname):
        text = _clean(value)
        if text:
            return text
    return (user.id or "your business").strip()


def _format_business_profile(user: User) -> Optional[str]:
    fields = [
        ("Business name", user.company),
        ("Workplace", user.organization_workplace),
        ("Owner", user.fullname),
        ("Email", user.email),
        ("Phone", user.phone or user.whatsapp_number),
        ("Occupation", user.occupation),
        ("Location", user.location or user.address),
        ("Branch", user.current_branch),
        ("Market", user.nationality),
    ]
    lines = [f"- {label}: {_clean(value)}" for label, value in fields if _clean(value)]
    social = []
    if _clean(user.instagram_url):
        social.append(f"instagram={_clean(user.instagram_url)}")
    if _clean(user.facebook_url):
        social.append(f"facebook={_clean(user.facebook_url)}")
    if _clean(user.twitter_url):
        social.append(f"twitter={_clean(user.twitter_url)}")
    if _clean(user.linkedin_url):
        social.append(f"linkedin={_clean(user.linkedin_url)}")
    if social:
        lines.append("- Social: " + "; ".join(social))
    if not lines:
        return None
    return "\n".join(lines)


def _format_order_line(order: Any) -> Optional[str]:
    number = _clean(getattr(order, "order_number", None)) or str(
        getattr(order, "order_id", "") or ""
    )
    if not number:
        return None
    customer = _clean(getattr(order, "customer_name", None)) or _clean(
        getattr(order, "customer_phone", None)
    ) or "customer"
    status = _enum_val(getattr(order, "order_status", None))
    payment = _enum_val(getattr(order, "payment_status", None))
    fulfillment = _enum_val(getattr(order, "fulfillment_status", None))
    total = getattr(order, "total_amount", None)
    currency = _clean(getattr(order, "currency_code", None)) or "GHS"
    items = _format_order_items(getattr(order, "order_items", None))
    bits = [f"- {number} | {customer}"]
    if status:
        bits.append(f"status={status}")
    if payment:
        bits.append(f"payment={payment}")
    if fulfillment:
        bits.append(f"fulfillment={fulfillment}")
    if total is not None:
        bits.append(f"total={currency} {total}")
    line = " | ".join(bits)
    if items:
        line += f" — {items}"
    return line


def _format_order_items(raw: Any) -> str:
    items: List[dict] = []
    if isinstance(raw, list):
        items = [i for i in raw if isinstance(i, dict)]
    elif isinstance(raw, dict):
        items = [raw]
    names = []
    for item in items[:4]:
        name = _clean(item.get("name") or item.get("item_name"), max_len=80)
        qty = item.get("quantity")
        if name and qty is not None:
            names.append(f"{name} x{qty}")
        elif name:
            names.append(name)
    return ", ".join(names)


def _format_inbox_line(summary: Any, *, waiting: bool) -> str:
    who = (
        _clean(getattr(summary, "user_fullname", None))
        or _clean(getattr(summary, "customer_phone", None))
        or _clean(getattr(summary, "user_id", None))
        or "customer"
    )
    last = _clean(getattr(summary, "last_message", None), max_len=160)
    flag = "WAITING" if waiting else "recent"
    if last:
        return f"- [{flag}] {who}: {last}"
    return f"- [{flag}] {who}"


def _excerpts_from_hits(hits: List[dict[str, Any]]) -> List[str]:
    excerpts: List[str] = []
    used = 0
    seen: List[str] = []
    for hit in hits:
        text = _clean(hit.get("text"), max_len=_EXCERPT_MAX)
        if len(text) < 20:
            continue
        lowered = text.lower()
        if any(lowered in existing or existing in lowered for existing in seen):
            continue
        pl = hit.get("payload") or {}
        meta = pl.get("metadata") if isinstance(pl, dict) else None
        tag = ""
        if isinstance(meta, dict):
            src = meta.get("source")
            fn = meta.get("file_name")
            url = meta.get("source_url")
            if src == "document" and fn:
                tag = f"document:{fn} | "
            elif src == "website" and url:
                tag = f"website:{url} | "
            elif src:
                tag = f"{src} | "
        line = f"- {tag}{text}"
        if used + len(line) + 1 > _RAG_CHAR_BUDGET:
            break
        excerpts.append(line)
        seen.append(lowered)
        used += len(line) + 1
    return excerpts


def _enum_val(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return _clean(value.value)
    return _clean(value)


def _clean(value: Any, *, max_len: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if max_len is not None and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text
