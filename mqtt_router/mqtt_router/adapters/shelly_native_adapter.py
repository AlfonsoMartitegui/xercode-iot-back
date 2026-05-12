from __future__ import annotations

import json
import logging
from datetime import datetime

from mqtt_router.adapters.path_utils import MISSING, get_path
from mqtt_router.adapters.value_converter import ValueConversionError, convert_value
from mqtt_router.topic_mapper import IncomingTopic

logger = logging.getLogger(__name__)


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
    mappings = _native_mappings_for_path(vendor_config, incoming.native_path)
    has_json_mappings = _has_json_mappings(mappings)
    json_payload = _decode_json_payload(payload_text) if has_json_mappings else None

    beaver_payload = {
        "device_id": incoming.device_id,
        "device_name": incoming.device_id,
        "vendor": incoming.vendor,
        "time": datetime.now().replace(microsecond=0).isoformat(),
    }

    added_fields = 0
    for mapping in mappings:
        try:
            value = _value_from_mapping(
                mapping,
                payload_text,
                json_payload,
                incoming.native_path,
                tolerate_errors=has_json_mappings,
            )
        except ValueConversionError as exc:
            raise ShellyNativeTransformError(str(exc)) from exc
        if value is MISSING:
            continue

        beaver_payload[mapping["target_key"]] = value
        added_fields += 1

    fw_device = beaver_payload.get("fw_device")
    if isinstance(fw_device, str) and fw_device:
        beaver_payload["device_name"] = fw_device

    if added_fields == 0:
        raise ShellyNativeTransformError(f"No values extracted for native path={incoming.native_path}")

    return json.dumps(beaver_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _native_mappings_for_path(
    vendor_config: dict[str, object],
    native_path: str,
) -> list[dict[str, object]]:
    native_topics = vendor_config.get("native_topics")
    if not isinstance(native_topics, dict):
        raise ShellyNativeTransformError("Vendor config missing native_topics object")

    mappings = native_topics.get("mappings")
    if not isinstance(mappings, list):
        raise ShellyNativeTransformError("Vendor config missing native_topics.mappings list")

    matched_mappings: list[dict[str, object]] = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise ShellyNativeTransformError("Native mapping must be an object")

        if mapping.get("native_path") != native_path:
            continue

        target_key = mapping.get("target_key")
        value_type = mapping.get("type")
        if not isinstance(target_key, str) or not isinstance(value_type, str):
            raise ShellyNativeTransformError("Native mapping requires target_key and type")

        normalized_mapping = {
            "target_key": target_key,
            "type": value_type,
            "value_map": mapping.get("value_map"),
        }
        payload_path = mapping.get("payload_path")
        if payload_path is not None:
            if not isinstance(payload_path, str):
                raise ShellyNativeTransformError("Native mapping payload_path must be a string")
            normalized_mapping["payload_path"] = payload_path

        matched_mappings.append(normalized_mapping)

    if matched_mappings:
        return matched_mappings

    raise ShellyNativeTransformError(f"Unsupported native path={native_path}")


def _has_json_mappings(mappings: list[dict[str, object]]) -> bool:
    return any("payload_path" in mapping for mapping in mappings)


def _decode_json_payload(payload_text: str) -> dict[str, object]:
    try:
        parsed_payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ShellyNativeTransformError("Invalid JSON payload for native mapping") from exc

    if not isinstance(parsed_payload, dict):
        raise ShellyNativeTransformError("Native JSON payload must be an object")

    return parsed_payload


def _value_from_mapping(
    mapping: dict[str, object],
    payload_text: str,
    json_payload: dict[str, object] | None,
    native_path: str,
    tolerate_errors: bool,
) -> object:
    payload_path = mapping.get("payload_path")
    if isinstance(payload_path, str):
        if json_payload is None:
            raise ShellyNativeTransformError("JSON payload is required for payload_path mapping")
        try:
            raw_value = get_path(json_payload, payload_path)
        except ValueError:
            logger.warning("Shelly native mapping skipped invalid payload_path=%s", payload_path)
            return MISSING
        if raw_value is MISSING:
            logger.debug("Shelly native field missing native_path=%s payload_path=%s", native_path, payload_path)
            return MISSING
    else:
        raw_value = payload_text

    try:
        return convert_value(
            raw_value,
            mapping["type"],
            _value_map(mapping.get("value_map")),
        )
    except ValueConversionError:
        if not tolerate_errors:
            raise
        logger.warning(
            "Shelly native field conversion failed native_path=%s target_key=%s",
            native_path,
            mapping["target_key"],
        )
        return MISSING


def _value_map(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ShellyNativeTransformError("Native mapping value_map must be an object")
    return {str(key).lower(): mapped_value for key, mapped_value in value.items()}
