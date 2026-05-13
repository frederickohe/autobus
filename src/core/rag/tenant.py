"""Resolve Qdrant `tenant_id` for payload isolation (per business or per user)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional


def _slug_part(value: str, *, max_len: int = 96) -> str:
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-") or "unknown"
    return s[:max_len]


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
