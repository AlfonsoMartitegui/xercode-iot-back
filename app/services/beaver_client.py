import json
from urllib import error, parse, request

from app.core.config import settings
from app.core.encryption import decrypt_secret
from app.models.tenant import Tenant


class BeaverConfigError(Exception):
    pass


class BeaverAuthError(Exception):
    pass


class BeaverConnectionError(Exception):
    pass


class BeaverClient:
    TOKEN_PATH = "/api/v1/oauth2/token"

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def test_auth(self) -> dict:
        payload = self._authenticate()
        return {
            "ok": True,
            "tenant_id": self.tenant.id,
            "beaver_base_url": self._base_url(),
            "authenticated_as": self.tenant.beaver_admin_username,
            "token_type": payload.get("token_type"),
            "expires_in": payload.get("expires_in"),
            "token_received": bool(payload.get("access_token")),
        }

    def _authenticate(self) -> dict:
        base_url = self._base_url()
        username = self.tenant.beaver_admin_username
        encrypted_password = self.tenant.beaver_admin_password_encrypted

        if not username or not encrypted_password:
            raise BeaverConfigError("Tenant Beaver technical credentials are incomplete")

        if not settings.BEAVER_CLIENT_ID or not settings.BEAVER_CLIENT_SECRET:
            raise BeaverConfigError("Global Beaver OAuth client credentials are incomplete")

        try:
            password = decrypt_secret(encrypted_password)
        except ValueError as exc:
            raise BeaverConfigError(str(exc)) from exc

        form_data = parse.urlencode(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": settings.BEAVER_CLIENT_ID,
                "client_secret": settings.BEAVER_CLIENT_SECRET,
            }
        ).encode("utf-8")

        req = request.Request(
            f"{base_url}{self.TOKEN_PATH}",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with request.urlopen(
                req,
                timeout=settings.BEAVER_HTTP_TIMEOUT_SECONDS,
            ) as response:
                raw_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BeaverAuthError(
                f"Beaver authentication failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise BeaverConnectionError(
                f"Could not connect to Beaver: {exc.reason}"
            ) from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise BeaverAuthError("Beaver returned a non-JSON authentication response") from exc

        token_data = data.get("data")
        if not isinstance(token_data, dict) or not token_data.get("access_token"):
            raise BeaverAuthError("Beaver authentication response did not include access_token")

        return token_data

    def _base_url(self) -> str:
        base_url = (self.tenant.beaver_base_url or "").strip().rstrip("/")
        if not base_url:
            raise BeaverConfigError("Tenant Beaver base URL is not configured")
        return base_url
