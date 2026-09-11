import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


def _build_fernet_key() -> bytes:
    secret = getattr(settings, "SECRET_KEY", "portfolio-contact-key")
    material = f"{secret}:portfolio-contact-protection".encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(material).digest())


def get_fernet() -> Fernet:
    key = getattr(settings, "FERNET_KEY", None)
    if key is None:
        key = _build_fernet_key()
    return Fernet(key)


def encrypt_value(value: str) -> str:
    if value is None:
        return ""
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    if not token:
        raise ValueError("Token vacío")
    return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
