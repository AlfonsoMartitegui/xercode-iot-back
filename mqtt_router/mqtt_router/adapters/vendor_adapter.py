from __future__ import annotations

import json
from datetime import datetime

from mqtt_router.adapters.path_utils import MISSING, get_path, set_path
from mqtt_router.topic_mapper import IncomingTopic


class VendorTransformError(Exception):
    pass


def transform_inbound(
    incoming: IncomingTopic,
    payload: bytes,
    vendor_config: dict[str, object],
) -> bytes:
    if not incoming.vendor or not incoming.device_id:
        raise VendorTransformError("Vendor and device_id are required for vendor transform")

    try:
        decoded_payload = payload.decode("utf-8")
        source_payload = json.loads(decoded_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VendorTransformError("Invalid JSON payload") from exc

    if not isinstance(source_payload, dict):
        raise VendorTransformError("Vendor payload must be a JSON object")

    canonical_payload: dict[str, object] = {
        "device_id": incoming.device_id,
        "vendor": incoming.vendor,
        "metrics": {},
        "status": {},
        "meta": _meta_from_config(vendor_config),
    }

    for mapping in _mappings_from_config(vendor_config):
        payload_path = mapping["payload_path"]
        target_path = mapping["target_path"]
        try:
            value = get_path(source_payload, payload_path)
            if value is MISSING:
                continue
            set_path(canonical_payload, target_path, value)
        except ValueError as exc:
            raise VendorTransformError("Vendor mapping path cannot be empty") from exc

    beaver_payload = _to_beaver_flat_payload(canonical_payload, source_payload, incoming)
    return json.dumps(beaver_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _to_beaver_flat_payload(
    canonical_payload: dict[str, object],
    source_payload: dict[str, object],
    incoming: IncomingTopic,
) -> dict[str, object]:
    metrics = canonical_payload.get("metrics")
    status = canonical_payload.get("status")
    if not isinstance(metrics, dict) or not isinstance(status, dict):
        raise VendorTransformError("Canonical metrics and status must be objects")

    device_name = source_payload.get("device_name")
    if device_name is None:
        device_name = incoming.device_id

    event_time = source_payload.get("time")
    if event_time is None:
        event_time = source_payload.get("ts")
    if event_time is None:
        event_time = datetime.now().replace(microsecond=0).isoformat()

    beaver_payload: dict[str, object] = {
        "device_id": incoming.device_id,
        "device_name": device_name,
        "vendor": incoming.vendor,
    }
    beaver_payload.update(metrics)
    beaver_payload.update(status)
    beaver_payload["time"] = event_time

    return beaver_payload


def _mappings_from_config(vendor_config: dict[str, object]) -> list[dict[str, str]]:
    inbound = vendor_config.get("inbound")
    if not isinstance(inbound, dict):
        raise VendorTransformError("Vendor config missing inbound object")

    mappings = inbound.get("mappings")
    if not isinstance(mappings, list):
        raise VendorTransformError("Vendor config missing inbound.mappings list")

    normalized_mappings: list[dict[str, str]] = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise VendorTransformError("Vendor mapping must be an object")

        payload_path = mapping.get("payload_path")
        target_path = mapping.get("target_path")
        if not isinstance(payload_path, str) or not isinstance(target_path, str):
            raise VendorTransformError("Vendor mapping requires payload_path and target_path")

        normalized_mappings.append(
            {
                "payload_path": payload_path,
                "target_path": target_path,
            }
        )

    return normalized_mappings


def _meta_from_config(vendor_config: dict[str, object]) -> dict[str, object]:
    meta = vendor_config.get("meta", {})
    if not isinstance(meta, dict):
        raise VendorTransformError("Vendor config meta must be an object")

    return dict(meta)
