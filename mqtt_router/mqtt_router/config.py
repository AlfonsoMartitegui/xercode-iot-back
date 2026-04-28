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
class AppConfig:
    central_mqtt: CentralMqttConfig
    tenant_mqtt_defaults: TenantMqttDefaults
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
            topic=os.getenv("CENTRAL_MQTT_TOPIC", "xercode/+/+/telemetry").strip()
            or "xercode/+/+/telemetry",
            client_id=os.getenv("CENTRAL_MQTT_CLIENT_ID", "xercode-mqtt-router").strip()
            or "xercode-mqtt-router",
        ),
        tenant_mqtt_defaults=TenantMqttDefaults(
            username=_optional_env("TENANT_MQTT_DEFAULT_USERNAME"),
            password=_optional_env("TENANT_MQTT_DEFAULT_PASSWORD"),
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
