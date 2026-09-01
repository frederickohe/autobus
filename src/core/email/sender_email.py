"""Normalize and read the outbound From address used by Zeptomail."""

from __future__ import annotations

import os
import re
from typing import Any, Optional

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class SenderEmailNotConfigured(ValueError):
    """Raised when a user tries to send mail without a From address."""


class SenderEmailInvalid(ValueError):
    """Raised when the submitted From address cannot be used."""


def sender_domain() -> str:
    return (os.getenv("ZEPTOMAIL_SENDER_DOMAIN") or "useautobus.com").strip().lower()


def sender_email_from_user(user: Any) -> Optional[str]:
    if user is None:
        return None
    getter = getattr(user, "get_agent", None)
    agent = getter("email_agent") if callable(getter) else None
    if not agent:
        return None
    raw = (agent.get("params") or {}).get("sender_email")
    text = str(raw or "").strip()
    return text or None


def normalize_sender_email(raw: str) -> str:
    """
    Accept a full address, a local part, or `noreply.useautobus.com`.

    All of these become `noreply@useautobus.com` when the sender domain is
    `useautobus.com`.
    """
    text = (raw or "").strip()
    if not text:
        raise SenderEmailInvalid(
            f"Enter a from email, for example noreply@{sender_domain()}"
        )

    domain = sender_domain()
    if "@" not in text:
        suffix = f".{domain}"
        lower = text.lower()
        if lower.endswith(suffix) and lower != domain:
            local = text[: -len(suffix)].strip()
            text = f"{local}@{domain}"
        else:
            text = f"{text}@{domain}"

    local, _, host = text.partition("@")
    local = local.strip()
    host = host.strip().lower()
    if not local or not host:
        raise SenderEmailInvalid(
            f"Enter a from email, for example noreply@{domain}"
        )
    if host != domain:
        raise SenderEmailInvalid(
            f"From email must use @{domain}, for example noreply@{domain}"
        )

    email = f"{local}@{host}"
    if not _EMAIL_RE.match(email):
        raise SenderEmailInvalid(
            f"That does not look like a valid from email. Try noreply@{domain}"
        )
    return email
