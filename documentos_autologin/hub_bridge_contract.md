# HUB Bridge Contract

## Objetivo

Definir de forma exacta y sin ambiguedad lo que debe hacer el proyecto HUB para iniciar el puente de autologin hacia Beaver Web.

Este documento cubre exclusivamente el lado HUB.

## Responsabilidad Del HUB

El HUB debe:

- autenticar al usuario en el HUB;
- decidir si ese usuario puede ser redirigido a Beaver;
- resolver el tenant Beaver correcto;
- emitir un `handoff token` corto y firmado;
- construir la URL de Beaver Web con ese token;
- redirigir al navegador.

El HUB no debe:

- intentar escribir en el `localStorage` de Beaver;
- entregar directamente un `access_token` Beaver al navegador como contrato final;
- depender de password reversible de usuario como base del puente;
- saltarse la comprobacion de membership/tenant.

## Momento De Uso

Este flujo aplica cuando:

- el usuario ya ha hecho login correctamente en HUB;
- el usuario no es un actor administrativo que deba quedarse en el panel HUB;
- el usuario tiene un tenant Beaver operativo al que debe ser enviado.

## Endpoint O Punto De Entrada En HUB

Hay dos modelos posibles.

### Modelo A. Redirect inmediato tras login

Tras login correcto en HUB:

- el backend responde con:
  - `redirect_mode = beaver_bridge`
  - `redirect_url = <url_final_beaver_bridge>`

o el frontend HUB hace la redireccion inmediatamente con datos devueltos por HUB.

### Modelo B. Endpoint explicito de lanzamiento

HUB expone un endpoint especifico tipo:

- `POST /auth/beaver/launch`
- o `POST /session/beaver/launch`

Este endpoint:

- usa la sesion HUB ya autenticada;
- emite el `handoff token`;
- devuelve la URL Beaver final.

### Recomendacion

La recomendacion mas limpia es:

- `POST /auth/beaver/launch`

porque separa:

- login HUB
- lanzamiento Beaver

y evita meter demasiada logica en el login inicial.

## Contracto De Salida Del HUB

### Success response exacta recomendada

```json
{
  "ok": true,
  "launch_mode": "beaver_bridge",
  "tenant_id": 7,
  "tenant_code": "acme",
  "redirect_url": "https://beaver-acme.example.com/auth/hub-bridge?code=<handoff_token>"
}
```

### Reglas

- `redirect_url` es obligatoria si `launch_mode = beaver_bridge`;
- no debe devolverse password;
- no debe devolverse `access_token` Beaver en esta respuesta;
- el `handoff token` debe ir embebido en la URL final.

## Handoff Token Contract

El HUB debe emitir un JWT firmado.

### Algoritmo recomendado

- `RS256`

### Duracion exacta recomendada

- 60 segundos

### Claims exactos recomendados

```json
{
  "iss": "https://hub.example.com",
  "aud": "beaver-hub-bridge",
  "sub": "hub-user-123",
  "jti": "7d934f1a-6f0f-4d58-9d1d-5dc43d3f2e70",
  "iat": 1710000000,
  "nbf": 1710000000,
  "exp": 1710000060,
  "purpose": "beaver_web_handoff",
  "hub_user_id": 123,
  "email": "user@example.com",
  "nickname": "User Name",
  "hub_tenant_id": 7,
  "tenant_id": "default",
  "redirect_url": "https://beaver-acme.example.com",
  "membership_role": "user"
}
```

## Claims Obligatorios

- `iss`
- `aud`
- `sub`
- `jti`
- `iat`
- `exp`
- `purpose`
- `email`
- `tenant_id`

## Claims Recomendados

- `hub_user_id`
- `hub_tenant_id`
- `nickname`
- `redirect_url`
- `membership_role`

## Validaciones Obligatorias Antes De Emitir El Token

### 1. Sesion HUB valida

Debe existir sesion/autenticacion HUB valida.

### 2. Usuario activo

El usuario HUB debe estar activo.

### 3. Membership valida

Debe existir membership activa del usuario para el tenant objetivo.

### 4. Tenant con Beaver configurado

Debe existir como minimo:

- `redirect_url`
- `beaver_base_url`

Idealmente tambien:

- credenciales tecnicas Beaver validas ya configuradas.

### 5. Usuario previsto para Beaver

El HUB debe tener claro que ese usuario:

- ya existe en Beaver;
- o debia haber sido provisionado previamente.

El launch no debe hacer provisioning implicito.

## Regla De Existencia En Beaver

El HUB no debe emitir bridge alegremente si sabe que el usuario no ha sido provisionado.

Recomendacion:

- si existe estado local fiable de provisioning Beaver, usarlo;
- si no existe todavia, permitir un primer modelo operativo donde el error se resuelva en Beaver y degrade a login;
- pero el objetivo final debe ser que HUB conozca si el usuario esta preparado para bridge.

## Construccion De La URL Final

Formato exacto recomendado:

```txt
<tenant.redirect_url>/auth/hub-bridge?code=<url_encoded_handoff_token>
```

### Ejemplo

```txt
https://beaver-acme.example.com/auth/hub-bridge?code=eyJhbGciOiJSUzI1NiIs...
```

### Reglas

- usar `redirect_url` del tenant como base publica;
- no usar `beaver_base_url` para redireccion de navegador salvo que coincidan;
- codificar el token en URL correctamente.

## Configuracion Nueva Requerida En HUB

### Variables recomendadas

- `BEAVER_BRIDGE_ENABLED=true|false`
- `BEAVER_BRIDGE_ISSUER=https://hub.example.com`
- `BEAVER_BRIDGE_AUDIENCE=beaver-hub-bridge`
- `BEAVER_BRIDGE_PRIVATE_KEY=<PEM>`
- `BEAVER_BRIDGE_TOKEN_TTL_SECONDS=60`

### Distribucion De Claves

El HUB firma con clave privada.

Beaver backend valida con la clave publica correspondiente.

## Errores Del Lado HUB

### 400

Para:

- tenant Beaver no configurado;
- membership requerida ausente;
- usuario sin tenant operativo.

### 403

Para:

- usuario autenticado pero no autorizado a lanzar Beaver.

### 409

Para:

- usuario no provisionado en Beaver si decidis bloquear antes del salto.

### 503

Para:

- bridge deshabilitado por configuracion.

## Fallback Recomendado

Si el bridge no puede lanzarse en HUB:

- devolver error claro al frontend HUB;
- no redirigir a una URL rota;
- opcionalmente ofrecer redireccion simple a Beaver login solo si negocio lo acepta.

## Politica Recomendada Por Fases

### Fase 1

HUB:

- resuelve tenant;
- redirige al `redirect_url` Beaver sin autologin.

### Fase 2

HUB:

- emite `handoff token`;
- redirige a `/auth/hub-bridge?code=...`

### Fase 3

HUB:

- añade trazabilidad;
- añade conocimiento fiable de si el usuario Beaver esta provisionado;
- endurece bloqueos preventivos.

## Logging Y Auditoria En HUB

Debe registrarse:

- `hub_user_id`
- `email`
- `hub_tenant_id`
- `redirect_url`
- `jti`
- resultado:
  - `bridge_issued`
  - `bridge_denied_missing_membership`
  - `bridge_denied_missing_beaver_config`
  - `bridge_denied_user_not_ready`

No debe registrarse:

- token completo;
- secretos;
- claves privadas.

## Criterios De Aceptacion

1. El HUB puede emitir una URL de bridge valida para un usuario normal.
2. La URL apunta al Beaver Web correcto del tenant.
3. El token dura poco tiempo.
4. El token contiene la identidad y tenant necesarios.
5. El HUB no necesita password reversible para lanzar el bridge.

## Decision Recomendada

La decision recomendada para el HUB es:

- no almacenar password reversible de usuario como requisito del autologin;
- usar `handoff token` firmado;
- delegar la creacion de la sesion final a Beaver backend;
- usar `redirect_url` publica del tenant como punto de entrada de navegador.
