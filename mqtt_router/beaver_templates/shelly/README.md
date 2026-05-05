# Shelly Beaver Templates

This directory contains versioned copies of Beaver IoT templates related to the Shelly adapter.

`mqtt_router` does not consume these YAML files directly at runtime. They are kept here as exact, source-controlled copies of the templates that must be imported or configured in Beaver IoT.

`mqtt_router/mqtt_router/configs/vendors/shelly.json` and `shelly-generic.device-template.yaml` are paired:

- `shelly.json` defines how Shelly JSON and native MQTT telemetry are normalized.
- `shelly-generic.device-template.yaml` is an exact copy of the matching Beaver device template.
- If a new field is added to the adapter, it must also be added to the Beaver template.

The Beaver topic associated with this template is:

```text
beaver-iot/mqtt@default/mqtt-device/shelly/telemetry
```
