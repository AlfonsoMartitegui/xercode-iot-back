# mqtt_router

`mqtt_router` is a standalone Python service that routes MQTT messages between a central broker and the internal MQTT brokers used by Beaver IoT tenant instances running in Docker.

The service is intentionally independent from the HUB FastAPI backend. It lives in the same parent folder for convenience, but it does not import backend modules, expose HTTP endpoints, or depend on backend runtime state.

## Architecture

Devices publish telemetry to one central MQTT broker. `mqtt_router` subscribes to that broker, extracts the tenant and device from the topic, resolves the internal MQTT destination for that tenant, maps the topic to the Beaver format, and republishes the same payload to the tenant broker.

Internal Beaver MQTT brokers should not be exposed publicly. Only the central MQTT broker should be reachable by devices.

Current tenant resolution is mock based:

| Tenant | Internal MQTT |
| --- | --- |
| `tenant_a` | `localhost:18831` |
| `tenant_b` | `localhost:18832` |

The resolver is isolated in `mqtt_router/tenant_resolver.py` so it can later be replaced with a MySQL query or HUB API call.

## Install

```powershell
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` if your central broker or mock tenant ports are different.

## Run

From this folder:

```powershell
python -m mqtt_router.main
```

## Configuration

```env
CENTRAL_MQTT_HOST=localhost
CENTRAL_MQTT_PORT=1883
CENTRAL_MQTT_USERNAME=
CENTRAL_MQTT_PASSWORD=
CENTRAL_MQTT_TOPIC=xercode/+/+/telemetry
CENTRAL_MQTT_CLIENT_ID=xercode-mqtt-router

TENANT_MQTT_DEFAULT_USERNAME=
TENANT_MQTT_DEFAULT_PASSWORD=

LOG_LEVEL=INFO
```

## Topics

Input topic from central broker:

```text
xercode/{tenant_slug}/{device_id}/telemetry
```

Example:

```text
xercode/tenant_a/device_001/telemetry
```

Output topic to Beaver tenant broker:

```text
devices/{device_id}/telemetry
```

Example:

```text
devices/device_001/telemetry
```

The mapping is implemented in `mqtt_router/topic_mapper.py` so it can be changed without touching the bridge logic.

## Test Publish

With a central broker listening on `localhost:1883`, run:

```powershell
mosquitto_pub -h localhost -p 1883 -t "xercode/tenant_a/device_001/telemetry" -m "{\"temperature\":22.5}"
```

Expected logs:

```text
Message received from central topic=xercode/tenant_a/device_001/telemetry
Tenant resolved tenant=tenant_a host=localhost port=18831
Topic mapped source=xercode/tenant_a/device_001/telemetry target=devices/device_001/telemetry
Message published to tenant tenant=tenant_a host=localhost port=18831 topic=devices/device_001/telemetry
```

## Notes

- No FastAPI imports are used.
- No HTTP API is exposed.
- The current tenant publisher creates a temporary MQTT client per message.
- Production should use a persistent per-tenant connection pool/cache.
- Reverse routing from Beaver to the central broker is planned but not implemented yet.
