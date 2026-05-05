# MQTT Contracts

## Objetivo del mqtt_router

`mqtt_router` es un servicio independiente del backend HUB.

Su funcion es:

- Recibir mensajes desde un broker MQTT central.
- Interpretar el topic de entrada.
- Resolver el tenant destino.
- Normalizar el payload si aplica.
- Publicar el mensaje final hacia el broker MQTT interno de Beaver IoT del tenant.

El topic de salida hacia Beaver se mantiene configurado por `BEAVER_MQTT_OUTPUT_TOPIC`.

## Contratos MQTT de entrada soportados

### A. Legacy Xercode

```text
xercode/{tenant_slug}/telemetry
```

Este contrato espera un payload JSON plano. El router valida que sea JSON UTF-8 valido y lo republica compacto sin transformacion de campos.

Ejemplo topic:

```text
xercode/1234/telemetry
```

Payload:

```json
{
  "device_id": "sensor001",
  "device_name": "Sensor 1",
  "temperature": 20.0,
  "humidity": 56.4,
  "time": "2026-05-05T19:04:16"
}
```

### B. Vendor JSON normalizado

```text
xercode/{tenant_slug}/{vendor}/{device_id}/telemetry
```

Este contrato permite indicar fabricante y dispositivo en el topic. El payload JSON de entrada se transforma usando el adapter JSON del fabricante.

Ejemplo topic:

```text
xercode/1234/shelly/sensor002/telemetry
```

### C. Shelly nativo real

Para dispositivos Shelly reales, configurar el `Custom MQTT prefix` como:

```text
x/{tenant_slug}/sh/{device_id}/telemetry
```

Ejemplo:

```text
x/1234/sh/shellyplug0/telemetry
```

Con ese prefix, el broker central recibe topics nativos Shelly como:

```text
shellies/x/{tenant_slug}/sh/{device_id}/telemetry/{native_path}
```

Ejemplos:

```text
shellies/x/1234/sh/shellyplug0/telemetry/relay/0/power
shellies/x/1234/sh/shellyplug0/telemetry/relay/0/energy
shellies/x/1234/sh/shellyplug0/telemetry/relay/0
shellies/x/1234/sh/shellyplug0/telemetry/temperature
shellies/x/1234/sh/shellyplug0/telemetry/temperature_f
shellies/x/1234/sh/shellyplug0/telemetry/overtemperature
```

## Contrato de salida hacia Beaver

El router publica siempre hacia el topic configurado:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

La salida final hacia Beaver debe ser JSON plano.

Ejemplo Shelly real:

```json
{
  "device_id": "shellyplug0",
  "device_name": "shellyplug0",
  "vendor": "shelly",
  "power": 123.5,
  "time": "2026-05-05T19:04:09"
}
```

## Eventos parciales

Los Shelly nativos publican campos parciales en mensajes separados:

- `power`
- `energy`
- `output`
- `temperature`
- `temperature_f`
- `overtemperature`

El router no reconstruye un snapshot completo del dispositivo en esta fase.

Cada mensaje nativo Shelly se convierte y se publica como un evento parcial plano hacia Beaver.

## Adapters por JSON

Los mappings de fabricantes viven en:

```text
mqtt_router/configs/vendors/{vendor}.json
```

Actualmente `shelly.json` define:

- Mappings para payload JSON normalizado.
- Mappings para native topics.
- Conversiones de tipo, como `float`, `int`, `string` y `boolean`.
- `value_map` opcional para convertir valores como `on` y `off` a `true` y `false`.

El codigo Python aplica reglas genericas:

- Match de topic contra patrones con placeholders.
- Extraccion de variables como `tenant_slug`, `device_id` y `native_path`.
- Busqueda de mapping por `native_path`.
- Conversion de tipos.
- Construccion de salida plana hacia Beaver.

## Configuracion Shelly real

En el dispositivo Shelly, configurar:

```text
Custom MQTT prefix:
x/{tenant_slug}/sh/{device_id}/telemetry
```

Ejemplo real:

```text
x/1234/sh/shellyplug0/telemetry
```

## Ejemplos de entrada y salida

### Power

Entrada topic:

```text
shellies/x/1234/sh/shellyplug0/telemetry/relay/0/power
```

Payload:

```text
123.5
```

Salida hacia Beaver:

```json
{
  "device_id": "shellyplug0",
  "device_name": "shellyplug0",
  "vendor": "shelly",
  "power": 123.5,
  "time": "..."
}
```

### Relay output

Entrada topic:

```text
shellies/x/1234/sh/shellyplug0/telemetry/relay/0
```

Payload:

```text
on
```

Salida hacia Beaver:

```json
{
  "device_id": "shellyplug0",
  "device_name": "shellyplug0",
  "vendor": "shelly",
  "output": true,
  "time": "..."
}
```

## Limitaciones actuales

- Solo inbound.
- No comandos outbound.
- No control remoto de reles.
- No cache ni snapshot completo.
- No UI para editar adapters.
- No autodescubrimiento.
- Solo probado con Shelly Plug real y simuladores.

## Proximos pasos recomendados

- Crear template Beaver especifico para Shelly/Xercode.
- Crear snapshot/cache opcional por dispositivo.
- Agregar segundo fabricante para validar el motor generico.
- Anadir tests automaticos de topics y conversions.
