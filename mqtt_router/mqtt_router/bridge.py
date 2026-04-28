from __future__ import annotations

import json
import logging
import time

import paho.mqtt.client as mqtt

from mqtt_router.config import CentralMqttConfig
from mqtt_router.tenant_resolver import TenantMqttTarget, TenantResolver
from mqtt_router.topic_mapper import TopicMapper

logger = logging.getLogger(__name__)


def _payload_preview(payload: bytes, limit: int = 300) -> str:
    preview = payload[:limit].decode("utf-8", errors="replace")
    if len(payload) > limit:
        return f"{preview}..."
    return preview


class MqttBridge:
    def __init__(
        self,
        central_config: CentralMqttConfig,
        tenant_resolver: TenantResolver,
        topic_mapper: TopicMapper,
    ) -> None:
        self._central_config = central_config
        self._tenant_resolver = tenant_resolver
        self._topic_mapper = topic_mapper
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=central_config.client_id,
        )

        if central_config.username:
            self._client.username_pw_set(
                central_config.username,
                central_config.password,
            )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    def run_forever(self) -> None:
        logger.info(
            "Connecting to central MQTT broker host=%s port=%s topic=%s",
            self._central_config.host,
            self._central_config.port,
            self._central_config.topic,
        )
        self._client.connect(
            self._central_config.host,
            self._central_config.port,
            keepalive=60,
        )
        self._client.loop_forever(retry_first_connection=True)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            logger.error("Central MQTT connection failed reason=%s", reason_code)
            return

        logger.info("Connected to central MQTT broker")
        result, mid = client.subscribe(self._central_config.topic)
        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info(
                "Subscribed to central topic topic=%s mid=%s",
                self._central_config.topic,
                mid,
            )
        else:
            logger.error(
                "Central topic subscription failed topic=%s result=%s",
                self._central_config.topic,
                result,
            )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            logger.warning("Central MQTT disconnected unexpectedly reason=%s", reason_code)
        else:
            logger.info("Central MQTT disconnected")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        topic = message.topic
        logger.info("Message received from central topic=%s bytes=%s", topic, len(message.payload))

        incoming = self._topic_mapper.parse_incoming(topic)
        if incoming is None:
            logger.warning("Invalid topic received topic=%s", topic)
            return

        target = self._tenant_resolver.resolve(incoming.tenant_slug)
        if target is None:
            logger.warning("Tenant not found tenant=%s topic=%s", incoming.tenant_slug, topic)
            return

        logger.info(
            "Tenant resolved tenant=%s host=%s port=%s",
            target.tenant_slug,
            target.host,
            target.port,
        )

        tenant_topic = self._topic_mapper.to_tenant_topic(incoming)
        logger.info(
            "Topic mapped source=%s target=%s",
            topic,
            tenant_topic,
        )

        tenant_payload = self._prepare_beaver_payload(message.payload)
        if tenant_payload is None:
            logger.error(
                "Invalid JSON payload discarded tenant=%s topic=%s payload_preview=%s",
                target.tenant_slug,
                topic,
                _payload_preview(message.payload),
            )
            return

        try:
            self._publish_to_tenant(target, tenant_topic, tenant_payload)
        except Exception:
            logger.exception(
                "Failed to publish to tenant tenant=%s host=%s port=%s topic=%s",
                target.tenant_slug,
                target.host,
                target.port,
                tenant_topic,
            )

    def _prepare_beaver_payload(self, payload: bytes) -> bytes | None:
        try:
            decoded_payload = payload.decode("utf-8")
            parsed_payload = json.loads(decoded_payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        return json.dumps(parsed_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _publish_to_tenant(
        self,
        target: TenantMqttTarget,
        topic: str,
        payload: bytes,
    ) -> None:
        connected = False

        def on_connect(
            client: mqtt.Client,
            userdata: object,
            flags: mqtt.ConnectFlags,
            reason_code: mqtt.ReasonCode,
            properties: mqtt.Properties | None,
        ) -> None:
            nonlocal connected
            connected = not reason_code.is_failure
            logger.info(
                "Tenant MQTT connect result tenant=%s reason=%s",
                target.tenant_slug,
                reason_code,
            )

        def on_disconnect(
            client: mqtt.Client,
            userdata: object,
            disconnect_flags: mqtt.DisconnectFlags,
            reason_code: mqtt.ReasonCode,
            properties: mqtt.Properties | None,
        ) -> None:
            logger.warning(
                "Tenant MQTT disconnected tenant=%s reason=%s",
                target.tenant_slug,
                reason_code,
            )

        # TODO: Use a persistent per-tenant connection pool/cache in production.
        tenant_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"xercode-router-{target.tenant_slug}",
        )
        tenant_client.on_connect = on_connect
        tenant_client.on_disconnect = on_disconnect

        if target.username:
            tenant_client.username_pw_set(target.username, target.password)

        try:
            logger.info(
                "Connecting tenant MQTT tenant=%s host=%s port=%s username=%s topic=%s payload=%s",
                target.tenant_slug,
                target.host,
                target.port,
                target.username,
                topic,
                payload.decode("utf-8", errors="replace"),
            )

            tenant_client.connect(target.host, target.port, keepalive=30)
            tenant_client.loop_start()

            for _ in range(50):
                if connected:
                    break
                time.sleep(0.1)

            if not connected:
                raise RuntimeError("Tenant MQTT did not connect successfully")

            result = tenant_client.publish(topic, payload=payload, qos=0)
            result.wait_for_publish(timeout=5)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Tenant publish failed result={result.rc}")

            logger.info(
                "Message published to tenant tenant=%s host=%s port=%s topic=%s",
                target.tenant_slug,
                target.host,
                target.port,
                topic,
            )
        finally:
            tenant_client.loop_stop()
            tenant_client.disconnect()

    def stop(self) -> None:
        self._client.disconnect()

    # TODO: Add reverse bridge support for Beaver to central traffic.
