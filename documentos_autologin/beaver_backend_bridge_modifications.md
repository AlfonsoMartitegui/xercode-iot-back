# Beaver Backend Bridge Modifications

## Objetivo

Definir de forma exacta y sin ambiguedad las modificaciones necesarias en el proyecto:

- `E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot`

para soportar el puente HUB -> Beaver Web -> Beaver Backend.

Este documento no implementa codigo.

## Resultado Esperado

Beaver backend debe aceptar un token/codigo corto emitido por el HUB y, si es valido, devolver un `access_token` y `refresh_token` Beaver exactamente compatibles con Beaver Web.

## Principio

Beaver backend no debe fiarse de una query string sin validar.

Beaver backend debe:

- validar firma;
- validar expiracion;
- validar audience;
- validar issuer;
- validar tenant;
- validar usuario;
- validar un solo uso;
- emitir la sesion Beaver final.

## Nuevo Endpoint Requerido

### Ruta

Recomendacion exacta:

- `POST /api/v1/hub/session/exchange`

Alternativa aceptable:

- `POST /api/v1/auth/hub/exchange`

No se recomienda mezclarlo con `/oauth2/token` existente.

## Request Contract

### Content-Type

- `application/json`

### Body JSON exacto

```json
{
  "code": "<hub_handoff_token>"
}
```

### Reglas

- `code` es obligatorio;
- `code` debe ser string no vacio;
- no deben aceptarse arrays ni multiples valores;
- no debe aceptarse token en query string en backend exchange;
- la query string solo la consume Beaver Web y luego la envia por POST.

## Handoff Token Contract

El `code` debe ser un JWT firmado por el HUB.

### Algoritmo recomendado

- `RS256`

### Claims obligatorios

```json
{
  "iss": "https://hub.example.com",
  "aud": "beaver-hub-bridge",
  "sub": "hub-user-123",
  "jti": "uuid-unico-de-un-solo-uso",
  "iat": 1710000000,
  "exp": 1710000060,
  "nbf": 1710000000,
  "hub_user_id": 123,
  "email": "user@example.com",
  "nickname": "User Name",
  "tenant_id": "default",
  "hub_tenant_id": 7,
  "beaver_base_url": "https://beaver-tenant.example.com",
  "purpose": "beaver_web_handoff"
}
```

### Claims obligatorios minimos

- `iss`
- `aud`
- `sub`
- `jti`
- `iat`
- `exp`
- `email`
- `tenant_id`
- `purpose`

### Claim `purpose`

Debe valer exactamente:

- `beaver_web_handoff`

## Validaciones Obligatorias En Beaver Backend

### 1. Firma

Beaver backend debe validar la firma con la clave publica del HUB.

### 2. Expiracion

Debe rechazar tokens expirados.

### 3. Not before

Debe rechazar tokens no activos todavia si viene `nbf`.

### 4. Audience

Debe exigir:

- `aud = beaver-hub-bridge`

### 5. Issuer

Debe exigir un `iss` configurado y conocido.

### 6. Purpose

Debe exigir:

- `purpose = beaver_web_handoff`

### 7. One-time use

Debe comprobar que `jti` no se ha usado antes.

### 8. Tenant consistency

Debe comprobar que:

- el `tenant_id` del token es valido;
- coincide con el tenant de esta instancia Beaver si aplica;
- no se permite emitir sesion para otro tenant.

### 9. User lookup

Debe localizar al usuario Beaver.

Estrategia recomendada:

- buscar por `email` exacto en Beaver.

Si no existe:

- devolver error controlado;
- no crear usuario implicitamente en este endpoint.

### 10. User state

Debe comprobar que el usuario Beaver:

- existe;
- esta habilitado;
- tiene acceso al tenant/rol correspondiente segun el modelo Beaver.

## Response Contract

### Success HTTP status

- `200 OK`

### Success body exacto

Debe ser compatible con el contrato que Beaver Web ya consume.

Formato recomendado:

```json
{
  "status": "Success",
  "data": {
    "access_token": "<beaver_access_token>",
    "refresh_token": "<beaver_refresh_token>",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

### Regla importante

La respuesta debe conservar el mismo shape que hoy devuelve `POST /oauth2/token`.

## Errores Requeridos

### 400

Para:

- body invalido;
- `code` ausente;
- `purpose` invalido.

### 401

Para:

- firma invalida;
- token expirado;
- issuer invalido;
- audience invalida.

### 403

Para:

- token valido pero usuario sin derecho de acceso;
- tenant no permitido;
- usuario Beaver deshabilitado.

### 404

Para:

- usuario Beaver no encontrado.

### 409

Para:

- `jti` ya consumido.

### Respuesta error recomendada

Seguir el estilo actual de Beaver.

Ejemplo:

```json
{
  "status": "Error",
  "message": "Hub handoff token expired"
}
```

## Persistencia Requerida Para One-Time Use

Debe existir una persistencia de `jti` consumido.

Opciones aceptables:

- tabla SQL;
- Redis;
- almacenamiento transitorio con TTL.

Recomendacion:

- tabla o cache con TTL >= expiracion maxima del token + margen de seguridad.

Campos minimos:

- `jti`
- `issuer`
- `email`
- `tenant_id`
- `used_at`
- `expires_at`

## Configuracion Nueva Requerida

Beaver backend debe incorporar configuracion para el bridge.

### Variables/configuracion exacta recomendada

- `hub.bridge.enabled=true|false`
- `hub.bridge.issuer=https://hub.example.com`
- `hub.bridge.audience=beaver-hub-bridge`
- `hub.bridge.public-key=<PEM>`
- `hub.bridge.max-clock-skew-seconds=30`
- `hub.bridge.max-token-age-seconds=120`

## Reutilizacion Del Mecanismo OAuth Interno

El endpoint nuevo no debe inventar un formato de token nuevo para Beaver Web.

Debe reutilizar el mecanismo interno que ya usa Beaver para:

- `access_token`
- `refresh_token`
- claims JWT

Resultado:

- Beaver Web no necesita un cliente especial;
- solo necesita guardar el token como si viniera del login normal.

## Requisitos De Implementacion Interna

### Opcion recomendada

Implementar un servicio interno tipo:

- `HubSessionExchangeService`

Responsabilidades:

- validar JWT del HUB;
- validar `jti`;
- localizar usuario Beaver;
- emitir `OAuth2AccessTokenAuthenticationToken` o equivalente interno;
- devolver response shape compatible.

### No recomendado

- duplicar logica de generacion de tokens en otro sitio;
- devolver un token Beaver parcial;
- emitir un formato distinto a `oauth2/token`;
- crear usuarios Beaver automaticamente dentro del exchange.

## Logging Y Auditoria

Debe registrarse al menos:

- `jti`
- `email`
- `tenant_id`
- `issuer`
- resultado:
  - `success`
  - `invalid_signature`
  - `expired`
  - `user_not_found`
  - `tenant_mismatch`
  - `replayed`

No debe loguearse:

- el token completo;
- secretos;
- claves;
- refresh token completo.

## Comportamiento Si El Usuario Beaver No Existe

Regla exacta recomendada:

- el endpoint `exchange` no provisiona usuarios;
- si el usuario no existe, devuelve `404` o `403` controlado;
- el provisioning del usuario debe seguir siendo un paso previo del HUB.

## Criterios De Aceptacion

1. Un token valido emitido por HUB produce tokens Beaver validos.
2. Beaver Web puede usar esos tokens sin diferencias con el login normal.
3. Un token expirado es rechazado.
4. Un token con firma invalida es rechazado.
5. Un token reutilizado es rechazado.
6. Un usuario Beaver inexistente es rechazado de forma controlada.
7. Un tenant incorrecto es rechazado.

## No Objetivos

- no crear usuarios Beaver aqui;
- no decidir negocio de memberships HUB;
- no hacer fallback al login por password dentro del backend exchange;
- no aceptar passwords de usuario como alternativa dentro de este endpoint.
