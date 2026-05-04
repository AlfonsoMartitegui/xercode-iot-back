from __future__ import annotations

from dataclasses import dataclass
import logging
from time import monotonic
from urllib.parse import urlparse

from mqtt_router.config import MySqlTenantConfig

logger = logging.getLogger(__name__)


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
            "tenant_a": ("localhost", 1883),
            "tenant_b": ("localhost", 1883),
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


class MySqlTenantResolver(TenantResolver):
    def __init__(
        self,
        mysql_config: MySqlTenantConfig,
        default_username: str | None = None,
        default_password: str | None = None,
    ) -> None:
        if not mysql_config.database:
            raise ValueError("MYSQL_DATABASE or DB_NAME is required for mysql tenant resolver")
        if not mysql_config.user:
            raise ValueError("MYSQL_USER or DB_USER is required for mysql tenant resolver")

        self._mysql_config = mysql_config
        self._default_username = default_username
        self._default_password = default_password
        self._cache: dict[str, tuple[float, TenantMqttTarget | None]] = {}

    def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
        now = monotonic()
        cached = self._cache.get(tenant_slug)
        if cached is not None:
            expires_at, target = cached
            if expires_at > now:
                return target

        target = self._resolve_from_mysql(tenant_slug)
        self._cache[tenant_slug] = (
            now + self._mysql_config.cache_ttl_seconds,
            target,
        )
        return target

    def _resolve_from_mysql(self, tenant_slug: str) -> TenantMqttTarget | None:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise RuntimeError("pymysql is required for mysql tenant resolver") from exc

        connection = pymysql.connect(
            host=self._mysql_config.host,
            port=self._mysql_config.port,
            user=self._mysql_config.user,
            password=self._mysql_config.password,
            database=self._mysql_config.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code, beaver_base_url, beaver_mqtt_host, beaver_mqtt_port
                    FROM tenants
                    WHERE code = %s
                      AND is_active = 1
                    LIMIT 1
                    """,
                    (tenant_slug,),
                )
                row = cursor.fetchone()
        finally:
            connection.close()

        if row is None:
            logger.warning("Tenant not found or inactive tenant=%s", tenant_slug)
            return None

        host = row.get("beaver_mqtt_host") or _host_from_beaver_base_url(row["beaver_base_url"])
        if host is None:
            logger.error(
                "Tenant has invalid beaver_base_url tenant=%s beaver_base_url=%s",
                tenant_slug,
                row["beaver_base_url"],
            )
            return None

        return TenantMqttTarget(
            tenant_slug=tenant_slug,
            host=host,
            port=row.get("beaver_mqtt_port") or self._mysql_config.mqtt_port,
            username=self._default_username,
            password=self._default_password,
        )


def _host_from_beaver_base_url(beaver_base_url: str | None) -> str | None:
    if not beaver_base_url:
        return None

    value = beaver_base_url.strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.hostname:
        return parsed.hostname

    parsed = urlparse(f"//{value}")
    return parsed.hostname


class HubTenantResolver(TenantResolver):
    def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
        # TODO: Replace this with a HUB API request if direct MySQL is not desired.
        raise NotImplementedError("HubTenantResolver is not implemented yet")
