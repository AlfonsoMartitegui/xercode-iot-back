# Documentacion tecnica de mqtt_router

## 1. Objetivo del servicio

`mqtt_router` es un servicio Python independiente que actua como router o bridge MQTT entre:

- Un broker MQTT central o publico, usado por los dispositivos.
- Brokers MQTT internos de tenants Beaver IoT que se ejecutan en Docker.

El objetivo principal es evitar exponer publicamente un puerto MQTT distinto por cada tenant. Los dispositivos publican contra un broker central, y `mqtt_router` decide a que tenant interno reenviar cada mensaje.

Este componente esta dentro de la carpeta del backend del HUB solo por organizacion del workspace, pero debe tratarse como un proyecto independiente.

No depende de FastAPI, no importa modulos del backend, no expone endpoints HTTP y no usa frameworks web.

## 2. Estructura del proyecto

```text
mqtt_router/
  README.md
  DOCUMENTACION_TECNICA.md
  requirements.txt
  .env.example
  mqtt_router/
    __init__.py
    main.py
    config.py
    logger.py
    tenant_resolver.py
    topic_mapper.py
    bridge.py
```

### Archivos de raiz

`README.md`

Contiene una guia rapida de instalacion, ejecucion, arquitectura y prueba con `mosquitto_pub`.

`DOCUMENTACION_TECNICA.md`

Este documento. Explica el diseno interno, el flujo de mensajes y los puntos de modificacion.

`requirements.txt`

Declara las dependencias del servicio:

```text
paho-mqtt
python-dotenv
```

`.env.example`

Plantilla de variables de entorno para configurar broker central, credenciales por defecto de tenants y nivel de logs.

### Paquete Python

`mqtt_router/__init__.py`

Marca la carpeta como paquete Python y define la version inicial.

`mqtt_router/main.py`

Punto de entrada del servicio. Se ejecuta con:

```powershell
python -m mqtt_router.main
```

Responsabilidades:

- Cargar configuracion desde `.env`.
- Configurar logging.
- Crear el resolver mock de tenants.
- Crear el mapper de topics.
- Crear y ejecutar el bridge MQTT.
- Capturar `KeyboardInterrupt` para cierre manual.

`mqtt_router/config.py`

Contiene las dataclasses de configuracion:

- `CentralMqttConfig`
- `TenantMqttDefaults`
- `BeaverMqttConfig`
- `AppConfig`

Tambien contiene `load_config()`, que carga variables de entorno usando `python-dotenv`.

`mqtt_router/logger.py`

Configura el logging estandar de Python.

Formato actual:

```text
%(asctime)s %(levelname)s [%(name)s] %(message)s
```

`mqtt_router/tenant_resolver.py`

Contiene la resolucion tenant -> broker MQTT interno.

Clases principales:

- `TenantMqttTarget`
- `TenantResolver`
- `MockTenantResolver`
- `HubTenantResolver`

Actualmente `MockTenantResolver` usa un diccionario interno:

```text
tenant_a -> localhost:1883
tenant_b -> localhost:1883
```

`HubTenantResolver` queda preparado como punto de sustitucion futuro para consultar MySQL o una API del HUB.

`mqtt_router/topic_mapper.py`

Contiene la logica para interpretar topics de entrada y convertirlos en topics de salida.

Entrada actual:

```text
xercode/{tenant_slug}/telemetry
```

Salida actual:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

`mqtt_router/bridge.py`

Contiene la logica principal MQTT:

- Conexion al broker central.
- Suscripcion al topic central.
- Callback de conexion.
- Callback de desconexion.
- Callback de recepcion de mensajes.
- Resolucion del tenant.
- Mapeo del topic.
- Publicacion hacia el broker interno del tenant.

## 3. Flujo de ejecucion

### Paso 1: arranque

El usuario ejecuta:

```powershell
python -m mqtt_router.main
```

`main.py` llama a:

```python
config = load_config()
configure_logging(config.log_level)
```

Despues crea:

```python
resolver = MockTenantResolver(...)
mapper = TopicMapper()
bridge = MqttBridge(...)
```

Finalmente ejecuta:

```python
bridge.run_forever()
```

### Paso 2: conexion al broker central

`MqttBridge.run_forever()` conecta con el broker configurado:

```text
CENTRAL_MQTT_HOST
CENTRAL_MQTT_PORT
CENTRAL_MQTT_USERNAME
CENTRAL_MQTT_PASSWORD
CENTRAL_MQTT_CLIENT_ID
```

El cliente central usa `paho-mqtt` y configura reconexion basica:

```python
reconnect_delay_set(min_delay=1, max_delay=30)
```

### Paso 3: suscripcion

Cuando el cliente conecta correctamente, `_on_connect()` se suscribe al topic central configurado:

```text
CENTRAL_MQTT_TOPIC=xercode/+/telemetry
```

### Paso 4: recepcion de mensaje

Cuando llega un mensaje, `_on_message()` recibe:

- `message.topic`
- `message.payload`

Ejemplo:

```text
topic: xercode/tenant_a/telemetry
payload: {"device_id":"sensor001","device_name":"Sensor 1","temperature":23.5,"humidity":55,"time":"2026-04-28T16:20:00"}
```

### Paso 5: validacion y parseo del topic

`TopicMapper.parse_incoming()` valida que el topic tenga exactamente este formato:

```text
xercode/{tenant_slug}/telemetry
```

Si el topic no es valido:

- Se registra un warning.
- El proceso no se rompe.
- El mensaje se descarta.

### Paso 6: resolucion del tenant

El bridge llama a:

```python
target = tenant_resolver.resolve(incoming.tenant_slug)
```

Si el tenant no existe:

- Se registra un warning.
- El mensaje se descarta.

Si existe, se obtiene un `TenantMqttTarget` con:

- `tenant_slug`
- `host`
- `port`
- `username`
- `password`

### Paso 7: mapeo del topic

El bridge transforma el topic de entrada:

```text
xercode/tenant_a/telemetry
```

En topic de salida:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

Esta transformacion esta centralizada en:

```text
mqtt_router/topic_mapper.py
```

### Paso 8: publicacion al broker interno

El bridge crea un cliente MQTT temporal para el tenant:

```python
tenant_client = mqtt.Client(...)
tenant_client.connect(target.host, target.port, keepalive=30)
tenant_client.publish(topic, payload=payload, qos=0)
tenant_client.disconnect()
```

En produccion conviene sustituir esto por un pool o cache de conexiones persistentes por tenant para reducir latencia y coste de conexion.

## 4. Configuracion

La configuracion se carga desde `.env`.

Crear el archivo local:

```powershell
copy .env.example .env
```

Variables disponibles:

```env
CENTRAL_MQTT_HOST=localhost
CENTRAL_MQTT_PORT=1883
CENTRAL_MQTT_USERNAME=
CENTRAL_MQTT_PASSWORD=
CENTRAL_MQTT_TOPIC=xercode/+/telemetry
CENTRAL_MQTT_CLIENT_ID=xercode-mqtt-router

TENANT_MQTT_DEFAULT_USERNAME=mqtt@default
TENANT_MQTT_DEFAULT_PASSWORD=

BEAVER_MQTT_OUTPUT_TOPIC=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry

LOG_LEVEL=INFO
```

### CENTRAL_MQTT_HOST

Host del broker central.

Ejemplos:

```text
localhost
mqtt.example.com
broker.public.local
```

### CENTRAL_MQTT_PORT

Puerto del broker central. Por defecto:

```text
1883
```

### CENTRAL_MQTT_USERNAME y CENTRAL_MQTT_PASSWORD

Credenciales opcionales para el broker central.

Si `CENTRAL_MQTT_USERNAME` esta vacio, no se configura autenticacion.

### CENTRAL_MQTT_TOPIC

Topic al que se suscribe el router.

Valor por defecto:

```text
xercode/+/telemetry
```

### CENTRAL_MQTT_CLIENT_ID

Identificador del cliente MQTT usado para conectarse al broker central.

### TENANT_MQTT_DEFAULT_USERNAME y TENANT_MQTT_DEFAULT_PASSWORD

Credenciales opcionales usadas para publicar en los brokers internos de tenants.

La version actual aplica las mismas credenciales por defecto a todos los tenants mock.

### BEAVER_MQTT_OUTPUT_TOPIC

Topic completo de escritura que Beaver IoT espera para el dispositivo MQTT.

Valor por defecto:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

En la interfaz de Beaver normalmente solo se edita el sufijo, por ejemplo:

```text
beaver/telemetry
```

Pero para publicar por MQTT se debe usar el Device Topic completo.

### LOG_LEVEL

Nivel de logging.

Valores habituales:

```text
DEBUG
INFO
WARNING
ERROR
```

## 5. Instalacion

Entrar en la carpeta del proyecto:

```powershell
cd E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\mqtt_router
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Crear archivo `.env`:

```powershell
copy .env.example .env
```

Editar `.env` si es necesario.

## 6. Ejecucion

Desde la carpeta:

```powershell
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\mqtt_router
```

Ejecutar:

```powershell
python -m mqtt_router.main
```

Si todo esta correcto, el servicio intentara conectar al broker central y suscribirse al topic configurado.

## 7. Prueba manual con mosquitto_pub

Con un broker central escuchando en `localhost:1883`:

```powershell
mosquitto_pub -h localhost -p 1883 -t "xercode/tenant_a/telemetry" -m "{\"device_id\":\"sensor001\",\"device_name\":\"Sensor 1\",\"temperature\":23.5,\"humidity\":55,\"time\":\"2026-04-28T16:20:00\"}"
```

Resultado esperado en logs:

```text
Message received from central topic=xercode/tenant_a/telemetry
Tenant resolved tenant=tenant_a host=localhost port=1883
Topic mapped source=xercode/tenant_a/telemetry target=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
Message published to tenant tenant=tenant_a host=localhost port=1883 topic=beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

Para comprobar la publicacion en el tenant, puede levantarse un broker MQTT interno mock en el puerto `1883` y suscribirse a:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

## 8. Puntos de modificacion para adaptar

### Cambiar resolucion de tenants

Archivo:

```text
mqtt_router/tenant_resolver.py
```

Clase actual:

```python
class MockTenantResolver(TenantResolver):
```

Punto futuro:

```python
class HubTenantResolver(TenantResolver):
```

Aqui se debe implementar la consulta real a:

- MySQL del HUB.
- API interna del HUB.
- Servicio de descubrimiento.
- Archivo de configuracion externo.

Contrato esperado:

```python
def resolve(self, tenant_slug: str) -> TenantMqttTarget | None:
```

Debe devolver `None` si el tenant no existe o no esta activo.

Debe devolver `TenantMqttTarget` si el tenant existe.

### Cambiar formato de topic de entrada

Archivo:

```text
mqtt_router/topic_mapper.py
```

Metodo:

```python
parse_incoming()
```

Actualmente espera:

```text
xercode/{tenant_slug}/telemetry
```

Si se necesita otro formato, modificar el parseo aqui.

Ejemplos de formatos futuros:

```text
tenants/{tenant_slug}/beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
hub/{tenant_slug}/{device_id}/events
```

### Cambiar topic de salida hacia Beaver

Archivo:

```text
mqtt_router/topic_mapper.py
```

Metodo:

```python
to_tenant_topic()
```

Actualmente devuelve:

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

Si Beaver requiere otro formato, modificar solo este metodo.

### Cambiar credenciales por tenant

Archivo:

```text
mqtt_router/tenant_resolver.py
```

Actualmente las credenciales por defecto vienen de:

```text
TENANT_MQTT_DEFAULT_USERNAME
TENANT_MQTT_DEFAULT_PASSWORD
```

En una version real, cada `TenantMqttTarget` podria incluir credenciales propias:

```python
TenantMqttTarget(
    tenant_slug="tenant_a",
    host="...",
    port=1883,
    username="...",
    password="...",
)
```

### Sustituir cliente temporal por conexiones persistentes

Archivo:

```text
mqtt_router/bridge.py
```

Metodo:

```python
_publish_to_tenant()
```

Actualmente crea, conecta, publica y desconecta un cliente por mensaje.

Para produccion se recomienda:

- Mantener un cliente MQTT por tenant.
- Reutilizar conexiones.
- Detectar desconexiones.
- Reintentar publicaciones.
- Limitar numero de conexiones abiertas.
- Cerrar clientes inactivos.

### Anadir direccion inversa Beaver -> central

Archivo:

```text
mqtt_router/bridge.py
```

Existe un TODO para soporte inverso.

La direccion inversa permitiria:

```text
Beaver internal MQTT -> central MQTT
```

No esta implementada todavia.

Para anadirla se deberia decidir:

- Topics internos a escuchar.
- Topic central de salida.
- Resolver inverso tenant -> topic central.
- Estrategia de conexiones persistentes por tenant.

### Cambiar nivel o formato de logs

Archivo:

```text
mqtt_router/logger.py
```

Funcion:

```python
configure_logging()
```

Aqui se puede cambiar el formato, incluir JSON logs o integrarlo con observabilidad externa.

## 9. Manejo de errores

### Topic invalido

Si el topic no cumple el formato esperado:

- Se registra `warning`.
- El mensaje se descarta.
- El proceso continua.

### Tenant no encontrado

Si el resolver no encuentra el tenant:

- Se registra `warning`.
- El mensaje se descarta.
- El proceso continua.

### Fallo al publicar en tenant

Si falla conexion o publicacion:

- Se registra `error` con stack trace usando `logger.exception`.
- El proceso continua.

### Desconexion del broker central

`paho-mqtt` gestiona reconexion con delay basico:

```python
reconnect_delay_set(min_delay=1, max_delay=30)
```

## 10. Consideraciones de produccion

Antes de usar en produccion, revisar:

- TLS para broker central.
- TLS o red privada segura hacia brokers internos.
- Credenciales por tenant.
- Pool o cache de conexiones persistentes.
- Reintentos con backoff para publicacion a tenants.
- Dead letter queue o almacenamiento temporal si un tenant esta caido.
- Metricas de mensajes recibidos, publicados, descartados y fallidos.
- Healthcheck externo del proceso.
- Ejecucion como servicio del sistema o contenedor Docker.
- Logs estructurados.
- Limites de payload.
- Validacion de tenant activo.
- Control de permisos ACL en broker central.

## 11. Contrato actual de mensajes

### Entrada

```text
xercode/{tenant_slug}/telemetry
```

Payload:

```text
bytes sin modificar
```

El router no interpreta ni modifica el payload.

Antes de publicar hacia Beaver, el router valida que el payload sea JSON UTF-8 valido. Si es valido, lo normaliza a JSON compacto. Si no es valido, lo descarta y registra un error con una previsualizacion del payload.

### Salida

```text
beaver-iot/mqtt@default/mqtt-device/beaver/telemetry
```

Payload:

```text
igual al payload recibido
```

## 12. Resumen rapido

Instalar:

```powershell
pip install -r requirements.txt
```

Crear `.env`:

```powershell
copy .env.example .env
```

Ejecutar:

```powershell
python -m mqtt_router.main
```

Probar:

```powershell
mosquitto_pub -h localhost -p 1883 -t "xercode/tenant_a/telemetry" -m "{\"device_id\":\"sensor001\",\"device_name\":\"Sensor 1\",\"temperature\":23.5,\"humidity\":55,\"time\":\"2026-04-28T16:20:00\"}"
```
