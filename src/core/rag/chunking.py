"""Split long extracted text into overlapping chunks for embedding."""

from __future__ import annotations

from typing import List


def chunk_text_for_rag(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    if chunk_size < 200:
        chunk_size = 200
    if overlap < 0 or overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)

    if len(t) <= chunk_size:
        return [t]

    chunks: List[str] = []
    start = 0
    n = len(t)
    while start < n:
        end = min(start + chunk_size, n)
        piece = t[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        nxt = end - overlap
        start = nxt if nxt > start else end
    return chunks
