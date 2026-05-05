from __future__ import annotations

import json
from datetime import datetime

from mqtt_router.topic_mapper import IncomingTopic


class ShellyNativeTransformError(Exception):
    pass


def transform_shelly_native(incoming: IncomingTopic, payload: bytes) -> bytes:
    if not incoming.native_path or not incoming.device_id:
        raise ShellyNativeTransformError("Shelly native path and device_id are required")

    payload_text = payload.decode("utf-8", errors="strict").strip()
    field_name, value = _convert_native_value(incoming.native_path, payload_text)

    beaver_payload = {
        "device_id": incoming.device_id,
        "device_name": incoming.device_id,
        "vendor": "shelly",
        field_name: value,
        "time": datetime.now().replace(microsecond=0).isoformat(),
    }

    return json.dumps(beaver_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _convert_native_value(native_path: str, payload_text: str) -> tuple[str, object]:
    if native_path == "relay/0/power":
        return "power", _float_value(payload_text, native_path)

    if native_path == "relay/0/energy":
        return "energy", _number_value(payload_text, native_path)

    if native_path == "relay/0":
        normalized_payload = payload_text.lower()
        if normalized_payload == "on":
            return "output", True
        if normalized_payload == "off":
            return "output", False
        raise ShellyNativeTransformError(
            f"Unsupported Shelly relay payload path={native_path} payload={payload_text}"
        )

    if native_path == "temperature":
        return "temperature", _float_value(payload_text, native_path)

    if native_path == "temperature_f":
        return "temperature_f", _float_value(payload_text, native_path)

    if native_path == "overtemperature":
        return "overtemperature", _int_value(payload_text, native_path)

    raise ShellyNativeTransformError(f"Unsupported Shelly native path={native_path}")


def _float_value(payload_text: str, native_path: str) -> float:
    try:
        return float(payload_text)
    except ValueError as exc:
        raise ShellyNativeTransformError(
            f"Shelly payload is not a float path={native_path} payload={payload_text}"
        ) from exc


def _int_value(payload_text: str, native_path: str) -> int:
    try:
        return int(payload_text)
    except ValueError as exc:
        raise ShellyNativeTransformError(
            f"Shelly payload is not an integer path={native_path} payload={payload_text}"
        ) from exc


def _number_value(payload_text: str, native_path: str) -> int | float:
    try:
        value = float(payload_text)
    except ValueError as exc:
        raise ShellyNativeTransformError(
            f"Shelly payload is not numeric path={native_path} payload={payload_text}"
        ) from exc

    if value.is_integer():
        return int(value)

    return value
