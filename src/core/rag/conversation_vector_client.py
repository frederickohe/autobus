"""HTTP client for the containerized RAG API (Qdrant + TEI)."""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ConversationVectorClient:
    def __init__(self) -> None:
        self.base = (os.getenv("RAG_SERVICE_URL") or "").rstrip("/")
        self.api_key = (os.getenv("RAG_SERVICE_API_KEY") or "").strip()

    def enabled(self) -> bool:
        return bool(self.base)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def search(self, *, tenant_id: str, query: str, limit: int = 5) -> List[dict[str, Any]]:
        if not self.base:
            return []
        url = f"{self.base}/v1/query"
        payload = {"tenant_id": tenant_id, "query": query, "limit": limit}
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        return list(data.get("hits") or [])

    @staticmethod
    def format_context(hits: List[dict[str, Any]]) -> Optional[str]:
        if not hits:
            return None
        lines: List[str] = []
        for h in hits:
            role = h.get("role", "?")
            score = float(h.get("score") or 0.0)
            text = (h.get("text") or "").strip()
            if not text:
                continue
            lines.append(f"- ({role} | {score:.3f}) {text}")
        if not lines:
            return None
        return "\n".join(lines)

    def upsert_turns(
        self,
        *,
        tenant_id: str,
        points: List[dict[str, Any]],
    ) -> None:
        if not self.base:
            return
        url = f"{self.base}/v1/points/upsert"
        body = {"tenant_id": tenant_id, "points": points}
        with httpx.Client(timeout=45.0) as client:
            r = client.post(url, json=body, headers=self._headers())
            r.raise_for_status()
