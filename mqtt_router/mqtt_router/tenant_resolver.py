from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantMqttTarget:
    tenant_slug: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None


class TenantResolver:
    def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
        raise NotImplementedError


class MockTenantResolver(TenantResolver):
    def __init__(
        self,
        default_username: str | None = None,
        default_password: str | None = None,
    ) -> None:
        self._default_username = default_username
        self._default_password = default_password
        self._tenants: dict[str, tuple[str, int]] = {
            "tenant_a": ("localhost", 18831),
            "tenant_b": ("localhost", 18832),
        }

    def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
        target = self._tenants.get(tenant_slug)
        if target is None:
            return None

        host, port = target
        return TenantMqttTarget(
            tenant_slug=tenant_slug,
            host=host,
            port=port,
            username=self._default_username,
            password=self._default_password,
        )


class HubTenantResolver(TenantResolver):
    def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
        # TODO: Replace this with a MySQL query or HUB API request.
        raise NotImplementedError("HubTenantResolver is not implemented yet")
