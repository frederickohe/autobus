"""Normalize LLM output into plain text suitable for chat, SMS, and social posts."""

from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```(?:\w+)?\s*\n?(.*?)```", re.DOTALL)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)")
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def strip_markdown_formatting(text: str | None) -> str:
    """
    Remove common markdown markers from model output.

    Unwraps fenced/inline code instead of deleting it so JSON captions survive.
    Does not strip underscore italics, which would corrupt JSON keys and snake_case.
    """
    if not text:
        return ""

    response = str(text)
    response = _FENCE_RE.sub(r"\1", response)
    response = _BOLD_RE.sub(r"\1", response)
    response = _ITALIC_RE.sub(r"\1", response)
    response = _HEADING_RE.sub("", response)
    response = _INLINE_CODE_RE.sub(r"\1", response)
    response = _LINK_RE.sub(r"\1", response)
    response = response.replace("**", "")
    return response.strip()
