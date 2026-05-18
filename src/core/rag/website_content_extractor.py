"""Fetch a public web page and extract plain text for RAG indexing."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx
from markdownify import markdownify as html_to_markdown

logger = logging.getLogger(__name__)

_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
_MAX_TEXT_CHARS = 100_000
_FETCH_TIMEOUT_S = 30.0
_USER_AGENT = "AutobusRAGIndexer/1.0 (+https://greenbrain.ai)"
_STRIP_TAGS_RE = re.compile(
    r"<(script|style|noscript)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def _hostname_resolves_to_blocked_ip(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return True
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def validate_public_http_url(url: str) -> str:
    """Return normalized URL or raise ValueError."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are supported")
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local"):
        raise ValueError("URL host is not allowed")
    if _hostname_resolves_to_blocked_ip(host):
        raise ValueError("URL host is not allowed")
    return raw


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "website").replace(".", "_")
    path = (parsed.path or "").strip("/").replace("/", "_")
    base = f"{host}_{path}" if path else host
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "webpage"
    return f"{safe[:120]}.txt"


class WebsiteContentExtractor:
    @staticmethod
    async def fetch_text(url: str) -> str:
        """
        Download HTML from a public URL and return markdown-ish plain text.
        Raises ValueError for invalid/blocked URLs or empty extractable content.
        """
        normalized = validate_public_http_url(url)
        headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

        async with httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT_S,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            async with client.stream("GET", normalized, headers=headers) as response:
                response.raise_for_status()
                content_type = (response.headers.get("content-type") or "").lower()
                if content_type and "text/html" not in content_type and "text/plain" not in content_type:
                    raise ValueError(
                        f"Unsupported content type: {content_type.split(';')[0]}"
                    )

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > _MAX_DOWNLOAD_BYTES:
                        raise ValueError("Page is too large to index")
                    chunks.append(chunk)

        raw_bytes = b"".join(chunks)
        html = raw_bytes.decode("utf-8", errors="replace")

        if "text/plain" in content_type:
            text = html.strip()
        else:
            cleaned_html = _STRIP_TAGS_RE.sub("", html)
            text = html_to_markdown(cleaned_html, heading_style="ATX").strip()

        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            raise ValueError("No extractable text found on this page")

        if len(text) > _MAX_TEXT_CHARS:
            text = text[:_MAX_TEXT_CHARS] + "\n[Content truncated...]"

        return text
