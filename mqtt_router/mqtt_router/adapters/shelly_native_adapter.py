from __future__ import annotations

import json
from datetime import datetime

from mqtt_router.adapters.value_converter import ValueConversionError, convert_value
from mqtt_router.topic_mapper import IncomingTopic


class ShellyNativeTransformError(Exception):
    pass


def transform_shelly_native(
    incoming: IncomingTopic,
    payload: bytes,
    vendor_config: dict[str, object],
) -> bytes:
    if not incoming.vendor or not incoming.native_path or not incoming.device_id:
        raise ShellyNativeTransformError("Vendor, native_path and device_id are required")

    payload_text = payload.decode("utf-8", errors="strict").strip()
    mapping = _native_mapping_for_path(vendor_config, incoming.native_path)
    target_key = mapping["target_key"]

    try:
        converted_value = convert_value(
            payload_text,
            mapping["type"],
            _value_map(mapping.get("value_map")),
        )
    except ValueConversionError as exc:
        raise ShellyNativeTransformError(str(exc)) from exc

    beaver_payload = {
        "device_id": incoming.device_id,
        "device_name": incoming.device_id,
        "vendor": incoming.vendor,
        target_key: converted_value,
        "time": datetime.now().replace(microsecond=0).isoformat(),
    }

    return json.dumps(beaver_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _native_mapping_for_path(
    vendor_config: dict[str, object],
    native_path: str,
) -> dict[str, object]:
    native_topics = vendor_config.get("native_topics")
    if not isinstance(native_topics, dict):
        raise ShellyNativeTransformError("Vendor config missing native_topics object")

    mappings = native_topics.get("mappings")
    if not isinstance(mappings, list):
        raise ShellyNativeTransformError("Vendor config missing native_topics.mappings list")

    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise ShellyNativeTransformError("Native mapping must be an object")

        if mapping.get("native_path") != native_path:
            continue

        target_key = mapping.get("target_key")
        value_type = mapping.get("type")
        if not isinstance(target_key, str) or not isinstance(value_type, str):
            raise ShellyNativeTransformError("Native mapping requires target_key and type")

        return {
            "target_key": target_key,
            "type": value_type,
            "value_map": mapping.get("value_map"),
        }

    raise ShellyNativeTransformError(f"Unsupported native path={native_path}")


def _value_map(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ShellyNativeTransformError("Native mapping value_map must be an object")
    return {str(key).lower(): mapped_value for key, mapped_value in value.items()}
