"""HTTP client for the containerized RAG API (Qdrant + TEI)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, List, Optional

BatchProgressFn = Callable[[int, int], None]

import httpx

logger = logging.getLogger(__name__)

# Cap JSON length for DEBUG logs (full vectors / long transcripts can be huge).
_UPSERT_DEBUG_LOG_MAX_CHARS = 120_000


def format_points_upsert_payload_for_log(tenant_id: str, points: list[dict[str, Any]]) -> str:
    """JSON body as sent to POST /v1/points/upsert, truncated for safe logging."""
    body: dict[str, Any] = {"tenant_id": tenant_id, "points": points}
    raw = json.dumps(body, ensure_ascii=False, default=str)
    if len(raw) > _UPSERT_DEBUG_LOG_MAX_CHARS:
        return (
            raw[:_UPSERT_DEBUG_LOG_MAX_CHARS]
            + f"... [truncated, total JSON length {len(raw)} chars]"
        )
    return raw


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
            pl = h.get("payload") or {}
            meta = pl.get("metadata")
            tag = ""
            if isinstance(meta, dict):
                src = meta.get("source")
                fn = meta.get("file_name")
                if src == "document" and fn:
                    tag = f"document:{fn} | "
                elif src:
                    tag = f"{src} | "
            lines.append(f"- ({tag}{role} | {score:.3f}) {text}")
        if not lines:
            return None
        return "\n".join(lines)

    def upsert_turns(
        self,
        *,
        tenant_id: str,
        points: List[dict[str, Any]],
    ) -> None:
        self.upsert_points_batched(tenant_id=tenant_id, points=points, batch_size=8)

    def upsert_points_batched(
        self,
        *,
        tenant_id: str,
        points: List[dict[str, Any]],
        batch_size: int = 64,
        on_batch_complete: Optional[BatchProgressFn] = None,
    ) -> int:
        """POST /v1/points/upsert in batches. Returns total points accepted."""
        if not self.base or not points:
            return 0
        url = f"{self.base}/v1/points/upsert"
        total = 0
        bs = max(1, min(batch_size, 200))
        batches = [points[i : i + bs] for i in range(0, len(points), bs)]
        with httpx.Client(timeout=120.0) as client:
            for batch_idx, batch in enumerate(batches, start=1):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "RAG POST /v1/points/upsert batch offset=%d size=%s body=%s",
                        (batch_idx - 1) * bs,
                        len(batch),
                        format_points_upsert_payload_for_log(tenant_id, batch),
                    )
                r = client.post(
                    url,
                    json={"tenant_id": tenant_id, "points": batch},
                    headers=self._headers(),
                )
                r.raise_for_status()
                data = r.json()
                total += int(data.get("upserted") or len(batch))
                if on_batch_complete:
                    on_batch_complete(batch_idx, len(batches))
        return total
