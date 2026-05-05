# mqtt_router

`mqtt_router` is a standalone Python service that routes MQTT messages between a central broker and the internal MQTT brokers used by Beaver IoT tenant instances running in Docker.

The service is intentionally independent from the HUB FastAPI backend. It lives in the same parent folder for convenience, but it does not import backend modules, expose HTTP endpoints, or depend on backend runtime state.

## Architecture

Devices publish telemetry to one central MQTT broker. `mqtt_router` subscribes to that broker, extracts the tenant from the topic, resolves the internal MQTT destination for that tenant, maps the topic to the Beaver format, and republishes the same payload to the tenant broker. The device id remains inside the payload, matching the Beaver IoT telemetry contract.

Internal Beaver MQTT brokers should not be exposed publicly. Only the central MQTT broker should be reachable by devices.

Current tenant resolution is mock based:

| Tenant | Internal MQTT |
| --- | --- |
| `tenant_a` | `localhost:1883` |
| `tenant_b` | `localhost:1883` |

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
CENTRAL_MQTT_TOPIC=#
CENTRAL_MQTT_CLIENT_ID=xercode-mqtt-router

TENANT_MQTT_DEFAULT_USERNAME=mqtt@default
TENANT_MQTT_DEFAULT_PASSWORD=

BEAVER_MQTT_OUTPUT_TOPIC=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry

TENANT_RESOLVER=mock
TENANT_CACHE_TTL_SECONDS=60
TENANT_MQTT_PORT=1883

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=

LOG_LEVEL=INFO
```

## Topics

Input topic from central broker:

```text
xercode/{tenant_slug}/telemetry
xercode/{tenant_slug}/{vendor}/{device_id}/telemetry
shellies/x/{tenant_slug}/sh/{device_id}/telemetry/...
```

Example:

```text
xercode/tenant_a/telemetry
xercode/tenant_a/shelly/shellyplug-123/telemetry
shellies/x/tenant_a/sh/shellyplug0/telemetry/relay/0/power
```

Output topic to Beaver tenant broker:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

Example:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

The mapping is implemented in `mqtt_router/topic_mapper.py` so it can be changed without touching the bridge logic.

Before publishing to Beaver, the router validates that the payload is valid UTF-8 JSON and normalizes it to compact JSON. Invalid JSON is discarded and logged.

When the input topic includes `{vendor}` and `{device_id}`, the router applies an inbound vendor adapter before publishing to the same Beaver output topic. Adapter rules are JSON files under `mqtt_router/configs/vendors/`.

Vendor adapters first build this internal canonical payload shape:

```json
{
  "device_id": "...",
  "vendor": "...",
  "metrics": {},
  "status": {},
  "meta": {}
}
```

That canonical object is internal only. Before publishing to Beaver, `metrics` and `status` are flattened into root fields, and `meta` is not published by default.

### Vendor adapters

Vendor adapters are generic JSON mappings. To add another vendor, create:

```text
mqtt_router/configs/vendors/{vendor}.json
```

Each mapping copies a value from the incoming JSON payload into the internal canonical payload:

```json
{
  "vendor": "example",
  "inbound": {
    "mappings": [
      {
        "payload_path": "source_value",
        "target_path": "metrics.target_value"
      }
    ]
  },
  "meta": {
    "source": "mqtt_router",
    "adapter": "json_mapping"
  }
}
```

Missing input fields are ignored. If the vendor config does not exist or the payload cannot be transformed, the message is discarded and the MQTT loop keeps running.

For vendor topics, the payload published to Beaver is flat. `device_id` always comes from the MQTT topic, even if the original payload also includes `device_id`. `device_name` comes from the original payload when present; otherwise it uses the topic `device_id`. `time` comes from `time`, then `ts`, and if neither exists the router generates the current timestamp.

Shelly example:

```text
Topic:
xercode/tenant_a/shelly/shellyplug-123/telemetry
```

```json
{
  "temperature": 21.5,
  "apower": 42.1,
  "voltage": 230.4,
  "current": 0.18,
  "output": true,
  "ts": "2026-05-05T18:10:00"
}
```

Payload published to Beaver:

```json
{
  "device_id": "shellyplug-123",
  "device_name": "shellyplug-123",
  "vendor": "shelly",
  "temperature": 21.5,
  "power": 42.1,
  "voltage": 230.4,
  "current": 0.18,
  "output": true,
  "time": "2026-05-05T18:10:00"
}
```

### Native Shelly topics

Some Shelly devices publish native scalar topics under `shellies/#`. Configure the Shelly custom MQTT prefix with the short contract:

```text
x/{tenant_slug}/sh/{device_id}/telemetry
```

The router accepts the resulting native topics:

```text
shellies/x/{tenant_slug}/sh/{device_id}/telemetry/{native_path...}
```

These messages are published to Beaver as partial flat telemetry events. The router does not cache or rebuild complete device state.

For native Shelly topics:

```text
tenant_slug = {tenant_slug}
vendor = shelly
device_id = {device_id}
device_name = {device_id}
```

Supported native paths:

| Topic suffix | Example payload | Beaver field |
| --- | --- | --- |
| `relay/0/power` | `0.00` | `power: 0.0` |
| `relay/0/energy` | `0` / `12.5` | `energy: 0` / `12.5` |
| `relay/0` | `on` / `off` | `output: true` / `false` |
| `temperature` | `33.46` | `temperature: 33.46` |
| `temperature_f` | `92.23` | `temperature_f: 92.23` |
| `overtemperature` | `0` | `overtemperature: 0` |

Example:

```text
shellies/x/1234/sh/shellyplug0/telemetry/temperature
```

```text
33.46
```

Payload published to Beaver:

```json
{
  "device_id": "shellyplug0",
  "device_name": "shellyplug0",
  "vendor": "shelly",
  "temperature": 33.46,
  "time": "2026-05-05T18:30:00"
}
```

Unsupported native paths or non-convertible payloads are discarded with a warning. The older `shellies/xercode/{tenant_slug}/telemetry/...` shape is intentionally discarded because it does not carry a reliable device id.

## Tenant Resolver

By default the router can use the mock resolver. For the real HUB database, set:

```env
TENANT_RESOLVER=mysql
TENANT_CACHE_TTL_SECONDS=60
TENANT_MQTT_PORT=1883
```

The MySQL resolver reads `tenants.beaver_base_url` by `tenants.code` and `is_active = 1`. It removes `http://`, `https://`, and any HTTP port, then uses the resulting host with MQTT port `1883`.

Example:

```text
xercode/1234/telemetry -> tenants.code=1234 -> beaver_base_url=http://localhost -> localhost:1883
```

## Test Publish

With a central broker listening on `localhost:1883`, run:

```powershell
mosquitto_pub -h localhost -p 1883 -t "xercode/tenant_a/telemetry" -m "{\"device_id\":\"sensor001\",\"device_name\":\"Sensor 1\",\"temperature\":23.5,\"humidity\":55,\"time\":\"2026-04-28T16:20:00\"}"
```

Expected logs:

```text
Message received from central topic=xercode/tenant_a/telemetry
Tenant resolved tenant=tenant_a host=localhost port=1883
Topic mapped source=xercode/tenant_a/telemetry target=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
Message published to tenant tenant=tenant_a host=localhost port=1883 topic=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

## Notes

- No FastAPI imports are used.
- No HTTP API is exposed.
- The current tenant publisher creates a temporary MQTT client per message.
- Production should use a persistent per-tenant connection pool/cache.
- Reverse routing from Beaver to the central broker is planned but not implemented yet.
