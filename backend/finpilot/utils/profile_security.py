from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from finpilot import config


def _fernet() -> Fernet:
    digest = hashlib.sha256(config.PROFILE_ENCRYPTION_SECRET.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_sensitive_value(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    token = _fernet().encrypt(text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_sensitive_value(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        raw = _fernet().decrypt(text.encode("utf-8"))
        return raw.decode("utf-8")
    except InvalidToken:
        return text


def mask_sensitive_value(value: str | None, prefix: int = 2, suffix: int = 2) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= prefix + suffix:
        return "*" * len(text)
    return f"{text[:prefix]}{'*' * (len(text) - prefix - suffix)}{text[-suffix:]}"
