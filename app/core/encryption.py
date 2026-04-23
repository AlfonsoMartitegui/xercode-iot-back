from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.BEAVER_CREDENTIALS_ENCRYPTION_KEY
    if not key:
        raise ValueError("BEAVER_CREDENTIALS_ENCRYPTION_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_secret(value: str) -> str:
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid Beaver credential or encryption key") from exc
