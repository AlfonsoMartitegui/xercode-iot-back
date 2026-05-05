from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class CentralMqttConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    topic: str
    client_id: str


@dataclass(frozen=True)
class TenantMqttDefaults:
    username: str | None
    password: str | None


@dataclass(frozen=True)
class BeaverMqttConfig:
    output_topic: str


@dataclass(frozen=True)
class MySqlTenantConfig:
    host: str
    port: int
    database: str | None
    user: str | None
    password: str | None
    cache_ttl_seconds: int
    mqtt_port: int


@dataclass(frozen=True)
class AppConfig:
    central_mqtt: CentralMqttConfig
    tenant_mqtt_defaults: TenantMqttDefaults
    beaver_mqtt: BeaverMqttConfig
    tenant_resolver: str
    mysql_tenant: MySqlTenantConfig
    log_level: str


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_config() -> AppConfig:
    load_dotenv()

    return AppConfig(
        central_mqtt=CentralMqttConfig(
            host=os.getenv("CENTRAL_MQTT_HOST", "localhost").strip() or "localhost",
            port=_int_env("CENTRAL_MQTT_PORT", 1883),
            username=_optional_env("CENTRAL_MQTT_USERNAME"),
            password=_optional_env("CENTRAL_MQTT_PASSWORD"),
            topic=os.getenv("CENTRAL_MQTT_TOPIC", "#").strip()
            or "#",
            client_id=os.getenv("CENTRAL_MQTT_CLIENT_ID", "xercode-mqtt-router").strip()
            or "xercode-mqtt-router",
        ),
        tenant_mqtt_defaults=TenantMqttDefaults(
            username=_optional_env("TENANT_MQTT_DEFAULT_USERNAME"),
            password=_optional_env("TENANT_MQTT_DEFAULT_PASSWORD"),
        ),
        beaver_mqtt=BeaverMqttConfig(
            output_topic=os.getenv(
                "BEAVER_MQTT_OUTPUT_TOPIC",
                "beaver-iot/mqtt@default/mqtt-device/beaver/telemetry",
            ).strip()
            or "beaver-iot/mqtt@default/mqtt-device/beaver/telemetry",
        ),
        tenant_resolver=os.getenv("TENANT_RESOLVER", "mock").strip().lower() or "mock",
        mysql_tenant=MySqlTenantConfig(
            host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")).strip() or "localhost",
            port=_int_env("MYSQL_PORT", _int_env("DB_PORT", 3306)),
            database=_optional_env("MYSQL_DATABASE") or _optional_env("DB_NAME"),
            user=_optional_env("MYSQL_USER") or _optional_env("DB_USER"),
            password=_optional_env("MYSQL_PASSWORD") or _optional_env("DB_PASS"),
            cache_ttl_seconds=_int_env("TENANT_CACHE_TTL_SECONDS", 60),
            mqtt_port=_int_env("TENANT_MQTT_PORT", 1883),
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
