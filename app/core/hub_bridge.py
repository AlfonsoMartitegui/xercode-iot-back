import base64
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from jose import jwt

from app.core.config import BASE_DIR, settings
from app.models.tenant import Tenant
from app.models.user import User


HUB_BRIDGE_ALGORITHM = "RS256"


class HubBridgeConfigurationError(RuntimeError):
    pass


def _load_private_key() -> str:
    if settings.HUB_BRIDGE_PRIVATE_KEY_PATH:
        key_path = settings.HUB_BRIDGE_PRIVATE_KEY_PATH
        if not os.path.isabs(key_path):
            key_path = os.path.join(BASE_DIR, key_path)
        try:
            with open(key_path, "r", encoding="utf-8") as key_file:
                raw_key = key_file.read()
        except OSError as exc:
            raise HubBridgeConfigurationError("HUB bridge private key file is not readable") from exc
    else:
        raw_key = settings.HUB_BRIDGE_PRIVATE_KEY

    raw_key = (raw_key or "").strip().strip('"').strip("'").replace("\\n", "\n")
    if not raw_key:
        raise HubBridgeConfigurationError("HUB bridge private key is not configured")

    if "BEGIN " in raw_key:
        return raw_key

    try:
        decoded = base64.b64decode(raw_key, validate=True)
    except ValueError as exc:
        raise HubBridgeConfigurationError("HUB bridge private key is invalid") from exc

    try:
        decoded_text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        decoded_text = ""

    if "BEGIN " in decoded_text:
        return decoded_text

    try:
        private_key = serialization.load_der_private_key(decoded, password=None)
    except ValueError as exc:
        raise HubBridgeConfigurationError("HUB bridge private key is invalid") from exc

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def build_beaver_exchange_url(beaver_base_url: str) -> str:
    return f"{beaver_base_url.rstrip('/')}/api/v1/hub/session/exchange"


def create_hub_handoff_token(
    *,
    user: User,
    tenant: Tenant,
) -> tuple[str, int, str]:
    expires_in = settings.HUB_BRIDGE_TOKEN_TTL_SECONDS
    now = datetime.now(timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = int((now + timedelta(seconds=expires_in)).timestamp())
    beaver_tenant_id = settings.HUB_BRIDGE_BEAVER_TENANT_ID

    claims = {
        "iss": settings.HUB_BRIDGE_ISSUER,
        "aud": settings.HUB_BRIDGE_AUDIENCE,
        "sub": str(user.id),
        "jti": str(uuid4()),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "purpose": settings.HUB_BRIDGE_PURPOSE,
        "email": user.email,
        "tenant_id": beaver_tenant_id,
        "hub_user_id": user.id,
        "hub_tenant_id": tenant.id,
        "nickname": user.username,
    }

    token = jwt.encode(claims, _load_private_key(), algorithm=HUB_BRIDGE_ALGORITHM)
    return token, expires_in, beaver_tenant_id
