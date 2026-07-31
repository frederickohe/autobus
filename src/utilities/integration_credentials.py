# Chatwoot Devise policy: upper, lower, digit, special. Appended to derived core.
CHATWOOT_PASSWORD_POLICY_SUFFIX = "Aa1!"

import hashlib
import hmac
import os


def _integration_secret() -> bytes:
    """
    Server-side secret for deriving integration passwords.
    Prefer INTEGRATION_PASSWORD_SECRET; fall back to JWT SECRET_KEY.
    """
    raw = (
        os.getenv("INTEGRATION_PASSWORD_SECRET")
        or os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or ""
    ).strip()
    if not raw:
        raise ValueError(
            "INTEGRATION_PASSWORD_SECRET or SECRET_KEY must be set to derive integration passwords"
        )
    return raw.encode("utf-8")


def integration_local_password(*, username: str) -> str:
    """
    LOCAL password for hosted Postiz accounts provisioned by Autobus.

    Derived via HMAC so knowing the username alone is not enough to authenticate
    to Postiz/Chatwoot. Still deterministic so the backend can re-derive it.
    """
    pwd = (username or "").strip()
    if not pwd:
        raise ValueError("username is required for integration local password")
    digest = hmac.new(_integration_secret(), pwd.encode("utf-8"), hashlib.sha256).hexdigest()
    # Chatwoot/Postiz need a memorable-enough printable password; hex is fine.
    return digest[:28]


def integration_chatwoot_password(*, username: str) -> str:
    """
    Chatwoot LOCAL password: HMAC-derived core + complexity suffix.
    """
    return f"{integration_local_password(username=username)}{CHATWOOT_PASSWORD_POLICY_SUFFIX}"
