from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomingTopic:
    tenant_slug: str
    device_id: str
    message_type: str


class TopicMapper:
    def parse_incoming(self, topic: str) -> IncomingTopic | None:
        parts = topic.split("/")
        if len(parts) != 4:
            return None

        root, tenant_slug, device_id, message_type = parts
        if root != "xercode" or message_type != "telemetry":
            return None

        if not tenant_slug or not device_id:
            return None

        return IncomingTopic(
            tenant_slug=tenant_slug,
            device_id=device_id,
            message_type=message_type,
        )

    def to_tenant_topic(self, incoming: IncomingTopic) -> str:
        return f"devices/{incoming.device_id}/{incoming.message_type}"
