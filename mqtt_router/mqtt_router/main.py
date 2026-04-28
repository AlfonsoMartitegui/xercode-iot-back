from __future__ import annotations

import logging

from mqtt_router.bridge import MqttBridge
from mqtt_router.config import load_config
from mqtt_router.logger import configure_logging
from mqtt_router.tenant_resolver import MockTenantResolver
from mqtt_router.topic_mapper import TopicMapper

logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)

    resolver = MockTenantResolver(
        default_username=config.tenant_mqtt_defaults.username,
        default_password=config.tenant_mqtt_defaults.password,
    )
    mapper = TopicMapper()
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
