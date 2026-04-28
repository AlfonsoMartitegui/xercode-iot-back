from __future__ import annotations

import logging

from mqtt_router.bridge import MqttBridge
from mqtt_router.config import load_config
from mqtt_router.logger import configure_logging
from mqtt_router.tenant_resolver import MockTenantResolver, MySqlTenantResolver, TenantResolver
from mqtt_router.topic_mapper import TopicMapper

logger = logging.getLogger(__name__)


def build_tenant_resolver(config) -> TenantResolver:
    if config.tenant_resolver == "mysql":
        return MySqlTenantResolver(
            mysql_config=config.mysql_tenant,
            default_username=config.tenant_mqtt_defaults.username,
            default_password=config.tenant_mqtt_defaults.password,
        )

    if config.tenant_resolver != "mock":
        raise ValueError(f"Unknown TENANT_RESOLVER value: {config.tenant_resolver}")

    return MockTenantResolver(
        default_username=config.tenant_mqtt_defaults.username,
        default_password=config.tenant_mqtt_defaults.password,
    )


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)

    resolver = build_tenant_resolver(config)
    mapper = TopicMapper(tenant_output_topic=config.beaver_mqtt.output_topic)
    bridge = MqttBridge(
        central_config=config.central_mqtt,
        tenant_resolver=resolver,
        topic_mapper=mapper,
    )

    try:
        bridge.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        bridge.stop()


if __name__ == "__main__":
    main()
