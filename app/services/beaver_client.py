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
    CREATE_MEMBER_PATH = "/api/v1/user/members"
    SEARCH_MEMBERS_PATH = "/api/v1/user/members/search"
    UPDATE_MEMBER_PATH_TEMPLATE = "/api/v1/user/members/{user_id}"
    ASSOCIATE_ROLE_PATH_TEMPLATE = "/api/v1/user/roles/{role_id}/associate-user"
    DISASSOCIATE_ROLE_PATH_TEMPLATE = "/api/v1/user/roles/{role_id}/disassociate-user"
    SEARCH_ROLES_PATH = "/api/v1/user/roles/search"

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

    def provision_user(self, *, email: str, nickname: str, password: str, role_id: str) -> dict:
        access_token = self._authenticate().get("access_token")
        existing_user = self.find_user_by_email(email=email, access_token=access_token)
        created_user = False

        if existing_user is None:
            self._post_json(
                self.CREATE_MEMBER_PATH,
                {
                    "email": email,
                    "nickname": nickname,
                    "password": password,
                },
                access_token=access_token,
            )
            created_user = True
            existing_user = self.find_user_by_email(email=email, access_token=access_token)

        if existing_user is None:
            raise BeaverAuthError("Beaver user was not found after provisioning attempt")

        self._post_json(
            self.ASSOCIATE_ROLE_PATH_TEMPLATE.format(role_id=role_id),
            {
                "role_id": role_id,
                "user_ids": [existing_user["user_id"]],
            },
            access_token=access_token,
        )

        return {
            "beaver_user_id": existing_user["user_id"],
            "created_user": created_user,
            "found_existing_user": not created_user,
            "role_associated": True,
            "role_id": role_id,
        }

    def list_roles(self) -> list[dict]:
        access_token = self._authenticate().get("access_token")
        payload = self._post_json(
            self.SEARCH_ROLES_PATH,
            {
                "page_number": 1,
                "page_size": 999,
            },
            access_token=access_token,
        )
        roles = payload.get("content") or []
        if not isinstance(roles, list):
            raise BeaverAuthError("Beaver role search response did not include a role list")
        return roles

    def update_user(self, *, email: str, nickname: str) -> dict:
        access_token = self._authenticate().get("access_token")
        existing_user = self.find_user_by_email(email=email, access_token=access_token)
        if existing_user is None:
            raise BeaverAuthError("Beaver user not found for update")

        beaver_user_id = str(existing_user["user_id"])
        self._send_json(
            path=self.UPDATE_MEMBER_PATH_TEMPLATE.format(user_id=beaver_user_id),
            payload={
                "user_id": beaver_user_id,
                "nickname": nickname,
                "email": email,
            },
            access_token=access_token,
            method="PUT",
        )
        return {
            "beaver_user_id": beaver_user_id,
            "updated": True,
        }

    def sync_user_role(self, *, email: str, old_role_id: str | None, new_role_id: str | None) -> dict:
        access_token = self._authenticate().get("access_token")
        existing_user = self.find_user_by_email(email=email, access_token=access_token)
        if existing_user is None:
            return {
                "synced": False,
                "skipped_reason": "beaver_user_not_found",
            }

        if old_role_id == new_role_id:
            return {
                "synced": True,
                "skipped_reason": "role_unchanged",
                "beaver_user_id": str(existing_user["user_id"]),
            }

        beaver_user_id = str(existing_user["user_id"])

        if old_role_id:
            self._post_json(
                self.DISASSOCIATE_ROLE_PATH_TEMPLATE.format(role_id=old_role_id),
                {
                    "role_id": old_role_id,
                    "user_ids": [beaver_user_id],
                },
                access_token=access_token,
            )

        if new_role_id:
            self._post_json(
                self.ASSOCIATE_ROLE_PATH_TEMPLATE.format(role_id=new_role_id),
                {
                    "role_id": new_role_id,
                    "user_ids": [beaver_user_id],
                },
                access_token=access_token,
            )

        return {
            "synced": True,
            "beaver_user_id": beaver_user_id,
            "removed_old_role": bool(old_role_id and old_role_id != new_role_id),
            "associated_new_role": bool(new_role_id),
        }

    def find_user_by_email(self, *, email: str, access_token: str) -> dict | None:
        payload = self._post_json(
            self.SEARCH_MEMBERS_PATH,
            {
                "page_size": 50,
                "page_num": 1,
                "keyword": email,
            },
            access_token=access_token,
        )
        users = payload.get("content") or []
        for user in users:
            if str(user.get("email", "")).strip().lower() == email.strip().lower():
                return user
        return None

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

    def _post_json(self, path: str, payload: dict, *, access_token: str) -> dict:
        return self._send_json(
            path=path,
            payload=payload,
            access_token=access_token,
            method="POST",
        )

    def _send_json(self, *, path: str, payload: dict, access_token: str, method: str) -> dict:
        req = request.Request(
            f"{self._base_url()}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                "Accept-Language": "EN",
            },
            method=method,
        )
        return self._read_json_response(req)

    def _read_json_response(self, req: request.Request) -> dict:
        try:
            with request.urlopen(
                req,
                timeout=settings.BEAVER_HTTP_TIMEOUT_SECONDS,
            ) as response:
                raw_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BeaverAuthError(
                f"Beaver request failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise BeaverConnectionError(
                f"Could not connect to Beaver: {exc.reason}"
            ) from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise BeaverAuthError("Beaver returned a non-JSON response") from exc

        payload = data.get("data")
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    def _base_url(self) -> str:
        base_url = (self.tenant.beaver_base_url or "").strip().rstrip("/")
        if not base_url:
            raise BeaverConfigError("Tenant Beaver base URL is not configured")
        return base_url
