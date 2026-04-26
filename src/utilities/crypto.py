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

    If `TOKEN_ENCRYPTION_KEY` is not set/invalid, returns the value as-is.
    """
    if value is None:
        return None
    f = _get_fernet()
    if not f:
        return value
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    """
    Decrypt secrets stored by `encrypt_secret`.

    If `TOKEN_ENCRYPTION_KEY` is not set/invalid, returns the value as-is.
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

