"""Credential encryption and session tokens.

One rule: a secret's plaintext never reaches the graph, a log line or the browser. Connector
credentials entered in the app are stored encrypted with a key derived from APP_SECRET_KEY; rotating
that key means re-entering them. Session cookies are random tokens stored only as a hash.
"""

import base64
import hashlib
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings

# Used only when APP_SECRET_KEY is empty (local development); `scripts/setup` writes a real one.
_DEV_KEY = "handovers-local-development-only"


@lru_cache
def _fernet() -> Fernet:
    raw = get_settings().app_secret_key.get_secret_value() or _DEV_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Raises `InvalidToken` when APP_SECRET_KEY changed since the value was stored."""
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def mask(plaintext: str) -> str:
    """What the browser may see of a stored secret: its last four characters."""
    return f"••••{plaintext[-4:]}" if len(plaintext) > 4 else "••••"


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """Sessions are stored by hash, so a graph dump yields no usable cookie."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = ["InvalidToken", "decrypt", "encrypt", "mask", "new_token", "token_hash"]
