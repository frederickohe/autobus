"""Shared RAG source labels for Qdrant intelligence points."""

from __future__ import annotations

from typing import List

DOCUMENT_SOURCE = "document"
WEBSITE_SOURCE = "website"
ONBOARDING_SOURCE = "onboarding"

# Indexed owner knowledge used by the customer webhook and owner copilot.
KNOWLEDGE_SOURCES: List[str] = [DOCUMENT_SOURCE, WEBSITE_SOURCE, ONBOARDING_SOURCE]

# File/URL uploads only — used when clearing uploaded intelligence.
UPLOAD_KNOWLEDGE_SOURCES: List[str] = [DOCUMENT_SOURCE, WEBSITE_SOURCE]
