import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Optional[Fernet]:
    key = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        return None


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """
    Encrypt secrets (API keys, OAuth tokens) before storing in DB.

    When REQUIRE_TOKEN_ENCRYPTION is true (default) and no key is configured,
    raises rather than storing plaintext.
    """
    if value is None:
        return None
    f = _get_fernet()
    if not f:
        require = os.getenv("REQUIRE_TOKEN_ENCRYPTION", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        debug = os.getenv("DEBUG", "false").strip().lower() in ("1", "true", "yes", "on")
        if require and not debug:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is required to store secrets. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return value
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    """
    Decrypt secrets stored by `encrypt_secret`.

    If `TOKEN_ENCRYPTION_KEY` is not set/invalid, returns the value as-is
    (supports legacy plaintext rows during migration).
    """
    if value is None:
        return None
    f = _get_fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Key mismatch or plaintext value stored
        return value
