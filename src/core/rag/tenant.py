"""Resolve Qdrant `tenant_id` for payload isolation (per business or per user)."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _slug_part(value: str, *, max_len: int = 96) -> str:
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-") or "unknown"
    return s[:max_len]


def resolve_effective_rag_tenant_id(
    user_data: Optional[Dict[str, Any]],
    *,
    fallback_db_user_id: Optional[Any] = None,
) -> Optional[str]:
    """
    Tenant id used for Qdrant payload filter + upserts.

    When RAG_USE_INTERNAL_USER_TENANT is true (default), always use internal DB user id:
      user:{db_user_id}
    so uploaded documents and WhatsApp conversational RAG share the same namespace.

    Set RAG_USE_INTERNAL_USER_TENANT=false to use resolve_rag_tenant_id() only (company/user modes).
    """
    raw = (os.getenv("RAG_USE_INTERNAL_USER_TENANT") or "true").strip().lower()
    use_internal = raw in ("1", "true", "yes", "on")
    db_uid = (user_data or {}).get("db_user_id")
    if db_uid is None and fallback_db_user_id is not None:
        db_uid = fallback_db_user_id
    if use_internal and db_uid is not None:
        result: Optional[str] = f"user:{db_uid}"
    else:
        result = resolve_rag_tenant_id(user_data)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("RAG resolve_effective_rag_tenant_id -> %r", result)
    return result


def resolve_rag_tenant_id(user_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Build a stable tenant key for Qdrant payload filtering.

    Modes (env `RAG_TENANT_MODE`):
    - `company_then_user` (default): company string if set, else user:{db_user_id}
    - `company`: company string only; None if missing
    - `user`: always user:{db_user_id} when db id exists
    """
    if not user_data:
        return None

    mode = (os.getenv("RAG_TENANT_MODE") or "company_then_user").strip().lower()
    db_uid = user_data.get("db_user_id")
    company = (user_data.get("company") or "").strip()

    if mode == "user":
        if db_uid is None:
            return None
        return f"user:{db_uid}"

    if mode == "company":
        if not company:
            return None
        return f"company:{_slug_part(company)}"

    # company_then_user
    if company:
        return f"company:{_slug_part(company)}"
    if db_uid is not None:
        return f"user:{db_uid}"
    return None
