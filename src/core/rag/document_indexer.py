"""Chunk extracted file text and upsert into the RAG API (Qdrant + TEI)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from core.rag.chunking import chunk_text_for_rag
from core.rag.conversation_vector_client import ConversationVectorClient
from core.rag.tenant import resolve_effective_rag_tenant_id

logger = logging.getLogger(__name__)

# Guardrail: very large uploads still create bounded vector points per request volume.
_MAX_CHUNKS = 300


def index_extracted_text_for_user(
    *,
    user_data: Dict[str, Any],
    object_key: str,
    file_name: str,
    extracted_text: str,
) -> Tuple[int, Optional[str]]:
    """
    Upsert document chunks for the resolved tenant (default: user:{db_user_id}).

    Returns (chunk_count_indexed, error_or_skip_reason).
    """
    tenant_id = resolve_effective_rag_tenant_id(user_data)
    if not tenant_id:
        return 0, "no_tenant_id"

    text = (extracted_text or "").strip()
    if not text:
        return 0, "no_extractable_text"

    client = ConversationVectorClient()
    if not client.enabled():
        return 0, "rag_service_disabled"

    chunks = chunk_text_for_rag(text)
    if len(chunks) > _MAX_CHUNKS:
        chunks = chunks[:_MAX_CHUNKS]
        truncated = True
    else:
        truncated = False

    points: list[dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        meta: dict[str, Any] = {
            "source": "document",
            "file_name": file_name,
            "object_key": object_key,
            "chunk_index": i,
        }
        if truncated and i == len(chunks) - 1:
            meta["truncated_run"] = True
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tenant_id}:{object_key}:{i}"))
        points.append(
            {
                "id": pid,
                "text": ch,
                "role": "system",
                "metadata": meta,
            }
        )

    try:
        n = client.upsert_points_batched(tenant_id=tenant_id, points=points)
        return n, ("truncated_to_max_chunks" if truncated else None)
    except Exception as e:
        logger.error("[RAG] document index upsert failed: %s", e, exc_info=True)
        return 0, f"upsert_failed:{e.__class__.__name__}"
