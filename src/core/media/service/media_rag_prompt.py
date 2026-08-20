"""Ground image/video generation prompts in the merchant's indexed business knowledge."""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from core.product.service.product_service import ProductService
from core.rag.conversation_vector_client import ConversationVectorClient
from core.rag.tenant import resolve_effective_rag_tenant_id
from core.user.model.User import User

logger = logging.getLogger(__name__)

_KNOWLEDGE_SOURCES = ["document", "website"]
_RAG_HIT_LIMIT = 12
_RAG_SCORE_THRESHOLD = 0.35
_RAG_CHAR_BUDGET = 2800
_PRODUCT_CHAR_BUDGET = 1200
_PRODUCT_LIMIT = 20
_EXCERPT_MAX = 420


def enrich_media_generation_prompt(
    prompt: str,
    db: Session,
    *,
    jwt_subject: str | None = None,
    req_user_id: str | None = None,
    media_kind: str = "image",
) -> str:
    """
    Return a generation prompt that includes RAG-indexed business facts relevant
    to ``prompt``. Falls back to the original prompt if lookup fails or nothing
    is indexed yet.
    """
    original = (prompt or "").strip()
    if not original:
        return prompt

    try:
        user = _resolve_user(db, jwt_subject, req_user_id)
        if not user:
            logger.info("[MEDIA_RAG] No user resolved; sending original prompt")
            return original

        profile = _format_business_profile(user)
        products = _format_product_catalog(db, user.id)
        knowledge = _format_rag_knowledge(user, original)

        if not profile and not products and not knowledge:
            logger.info(
                "[MEDIA_RAG] No business context for user=%s; sending original prompt",
                user.id,
            )
            return original

        kind = "video" if (media_kind or "").strip().lower() == "video" else "image"
        enriched = _compose_prompt(
            original,
            kind=kind,
            profile=profile,
            products=products,
            knowledge=knowledge,
        )
        logger.info(
            "[MEDIA_RAG] Enriched %s prompt user=%s profile=%s products=%s rag=%s chars=%s",
            kind,
            user.id,
            bool(profile),
            bool(products),
            bool(knowledge),
            len(enriched),
        )
        return enriched
    except Exception as e:
        logger.warning("[MEDIA_RAG] Prompt enrichment failed: %s", e, exc_info=True)
        return original


def _resolve_user(
    db: Session,
    jwt_subject: str | None,
    req_user_id: str | None,
) -> Optional[User]:
    for identifier in (jwt_subject, req_user_id):
        user = _find_user(db, identifier)
        if user:
            return user
    return None


def _find_user(db: Session, identifier: str | None) -> Optional[User]:
    ident = (identifier or "").strip()
    if not ident:
        return None
    return (
        db.query(User)
        .filter((User.id == ident) | (User.email == ident) | (User.phone == ident))
        .first()
    )


def _clean_text(value: Any, *, max_len: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if max_len is not None and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def _format_business_profile(user: User) -> Optional[str]:
    fields = [
        ("Business name", user.company),
        ("Workplace", user.organization_workplace),
        ("Occupation", user.occupation),
        ("Location", user.location or user.address),
        ("Branch", user.current_branch),
        ("Nationality / market", user.nationality),
    ]
    lines = [f"- {label}: {_clean_text(value)}" for label, value in fields if _clean_text(value)]
    if not lines:
        return None
    return "\n".join(lines)


def _format_product_catalog(db: Session, user_id: str) -> Optional[str]:
    try:
        products = ProductService(db).get_products_by_user(
            str(user_id), skip=0, limit=_PRODUCT_LIMIT
        )
    except Exception as e:
        logger.warning("[MEDIA_RAG] Product catalog lookup failed: %s", e, exc_info=True)
        return None
    if not products:
        return None

    lines: List[str] = []
    used = 0
    for product in products:
        name = _clean_text(getattr(product, "name", None))
        if not name:
            continue
        bits = [f"- {name}"]
        price = getattr(product, "price", None)
        if price is not None:
            bits.append(f"price={price}")
        category = _clean_text(getattr(product, "category", None))
        if category:
            bits.append(f"category={category}")
        desc = _clean_text(getattr(product, "description", None), max_len=160)
        line = " | ".join(bits)
        if desc:
            line += f" — {desc}"
        if used + len(line) + 1 > _PRODUCT_CHAR_BUDGET:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines) if lines else None


def _format_rag_knowledge(user: User, prompt: str) -> Optional[str]:
    client = ConversationVectorClient()
    if not client.enabled():
        logger.warning("[MEDIA_RAG] RAG_SERVICE_URL not configured; skipping indexed context")
        return None

    user_data = {
        "db_user_id": user.id,
        "company": user.company,
        "user_id": user.phone,
    }
    tenant_id = resolve_effective_rag_tenant_id(
        user_data,
        fallback_db_user_id=user.id,
    )
    if not tenant_id:
        logger.warning("[MEDIA_RAG] No tenant_id for user %s; skipping vector search", user.id)
        return None

    try:
        hits = client.search(
            tenant_id=tenant_id,
            query=prompt,
            limit=_RAG_HIT_LIMIT,
            score_threshold=_RAG_SCORE_THRESHOLD,
            sources=_KNOWLEDGE_SOURCES,
        )
    except Exception as e:
        logger.warning("[MEDIA_RAG] search failed for user %s: %s", user.id, e, exc_info=True)
        return None

    excerpts = _excerpts_from_hits(hits or [])
    logger.info(
        "[MEDIA_RAG] knowledge search tenant=%s hits=%s excerpts=%s",
        tenant_id,
        len(hits or []),
        len(excerpts),
    )
    return "\n".join(excerpts) if excerpts else None


def _excerpts_from_hits(hits: List[dict[str, Any]]) -> List[str]:
    excerpts: List[str] = []
    used = 0
    seen: List[str] = []
    for hit in hits:
        text = _clean_text(hit.get("text"), max_len=_EXCERPT_MAX)
        if len(text) < 20:
            continue
        lowered = text.lower()
        if any(lowered in existing or existing in lowered for existing in seen):
            continue
        line = f"- {text}"
        if used + len(line) + 1 > _RAG_CHAR_BUDGET:
            break
        excerpts.append(line)
        seen.append(lowered)
        used += len(line) + 1
    return excerpts


def _compose_prompt(
    user_prompt: str,
    *,
    kind: str,
    profile: Optional[str],
    products: Optional[str],
    knowledge: Optional[str],
) -> str:
    medium = "video" if kind == "video" else "image"
    sections = [
        f"Generate a marketing {medium} for this specific business.",
        "Use the business information below to make the result on-brand and specific "
        "(products, setting, audience, colors, and visual identity). Follow the creative "
        "brief as the scene to create. Do not invent products, brand names, logos, or "
        "facts that are not in the business information. Do not render this briefing as "
        "on-screen text unless the creative brief asks for copy.",
    ]
    if kind == "video":
        sections.append(
            "Make the video cinematic and commercially useful: clear subject, motion, "
            "and atmosphere that fit this business."
        )
    if profile:
        sections.extend(["", "BUSINESS PROFILE:", profile])
    if products:
        sections.extend(["", "PRODUCTS AND SERVICES:", products])
    if knowledge:
        sections.extend(["", "INDEXED BUSINESS KNOWLEDGE (retrieved for this brief):", knowledge])
    sections.extend(["", "CREATIVE BRIEF:", user_prompt])
    return "\n".join(sections)
