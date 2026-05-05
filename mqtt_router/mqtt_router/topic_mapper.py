from __future__ import annotations

from dataclasses import dataclass

from mqtt_router.adapters.mapping_loader import VendorConfigError, load_vendor_configs
from mqtt_router.adapters.native_topic_matcher import match_topic_pattern


@dataclass(frozen=True)
class IncomingTopic:
    tenant_slug: str
    message_type: str
    vendor: str | None = None
    device_id: str | None = None
    native_topic: bool = False
    native_path: str | None = None


class TopicMapper:
    def __init__(self, tenant_output_topic: str) -> None:
        self._tenant_output_topic = tenant_output_topic

    def parse_incoming(self, topic: str) -> IncomingTopic | None:
        parts = topic.split("/")

        native_topic = self._parse_native_topic(topic)
        if native_topic is not None:
            return native_topic

        if len(parts) == 3:
            root, tenant_slug, message_type = parts
            if root != "xercode" or message_type != "telemetry":
                return None

            if not tenant_slug:
                return None

            return IncomingTopic(
                tenant_slug=tenant_slug,
                message_type=message_type,
            )

        if len(parts) != 5:
            return None

        root, tenant_slug, vendor, device_id, message_type = parts
        if root != "xercode" or message_type != "telemetry":
            return None

        if not tenant_slug or not vendor or not device_id:
            return None

        return IncomingTopic(
            tenant_slug=tenant_slug,
            message_type=message_type,
            vendor=vendor,
            device_id=device_id,
        )

    def to_tenant_topic(self, incoming: IncomingTopic) -> str:
        return self._tenant_output_topic

    def _parse_native_topic(self, topic: str) -> IncomingTopic | None:
        try:
            vendor_configs = load_vendor_configs()
        except VendorConfigError:
            return None

        for vendor_config in vendor_configs:
            vendor = vendor_config.get("vendor")
            if not isinstance(vendor, str):
                continue

            native_topics = vendor_config.get("native_topics")
            if not isinstance(native_topics, dict):
                continue

            patterns = native_topics.get("patterns")
            if not isinstance(patterns, list):
                continue

            for pattern_config in patterns:
                if not isinstance(pattern_config, dict):
                    continue

                pattern = pattern_config.get("pattern")
                if not isinstance(pattern, str):
                    continue

                values = match_topic_pattern(
                    topic,
                    pattern,
                    native_path_mode=_optional_string(pattern_config.get("native_path_mode")),
                )
                if values is None:
                    continue

                tenant_slug = values.get("tenant_slug")
                device_id = values.get("device_id")
                native_path = values.get("native_path")
                if not tenant_slug or not device_id or not native_path:
                    return None

                return IncomingTopic(
                    tenant_slug=tenant_slug,
                    message_type="telemetry",
                    vendor=vendor,
                    device_id=device_id,
                    native_topic=True,
                    native_path=native_path,
                )

        return None


def _optional_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
