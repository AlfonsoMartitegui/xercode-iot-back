from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomingTopic:
    tenant_slug: str
    message_type: str


class TopicMapper:
    def __init__(self, tenant_output_topic: str) -> None:
        self._tenant_output_topic = tenant_output_topic

    def parse_incoming(self, topic: str) -> IncomingTopic | None:
        parts = topic.split("/")
        if len(parts) != 3:
            return None

        root, tenant_slug, message_type = parts
        if root != "xercode" or message_type != "telemetry":
            return None

        if not tenant_slug:
            return None

        return IncomingTopic(
            tenant_slug=tenant_slug,
            message_type=message_type,
        )

    def to_tenant_topic(self, incoming: IncomingTopic) -> str:
        return self._tenant_output_topic
