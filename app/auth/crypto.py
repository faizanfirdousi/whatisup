import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings


def fernet_key_bytes() -> bytes:
    """Stable Fernet key from TOKEN_ENCRYPTION_KEY, or a derivation of SESSION_SECRET for local dev."""
    raw = (get_settings().token_encryption_key or "").strip()
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
        try:
            Fernet(key)
            return key
        except Exception:
            pass
        digest = hashlib.sha256(raw.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    digest = hashlib.sha256(get_settings().session_secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    return Fernet(fernet_key_bytes())


def encrypt_token(token: str) -> str:
    return get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return get_fernet().decrypt(encrypted.encode()).decode()
