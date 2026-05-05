from __future__ import annotations

from dataclasses import dataclass


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

        if len(parts) >= 7 and parts[:2] == ["shellies", "x"]:
            _, root, tenant_slug, vendor_marker, device_id, message_type, *native_path_parts = parts
            if root != "x" or vendor_marker != "sh" or message_type != "telemetry":
                return None

            if not tenant_slug or not device_id or not native_path_parts:
                return None

            return IncomingTopic(
                tenant_slug=tenant_slug,
                message_type=message_type,
                vendor="shelly",
                device_id=device_id,
                native_topic=True,
                native_path="/".join(native_path_parts),
            )

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
