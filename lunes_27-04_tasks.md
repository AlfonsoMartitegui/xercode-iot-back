# Lunes 27-04 - Tareas HUB -> Beaver Bridge Redirect

## Objetivo del documento

Este documento deja preparado el contexto completo para retomar el lunes el siguiente bloque de trabajo:

```text
Login de usuario normal en HUB -> handoff/redirect a Beaver usando el bridge ya implementado en Beaver backend Spring Boot
```

Debe servir tanto para:

- Codex trabajando en backend HUB:
  - `E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack`
- Codex trabajando en frontend HUB:
  - `E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront`
- Codex o humano revisando Beaver backend:
  - `E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot`

## Estado validado antes de empezar

Ya esta validado el alta completa de usuario desde frontend HUB:

```text
crear usuario HUB -> crear membresia HUB -> provisionar Beaver -> asociar rol Beaver
```

Validacion confirmada en:

```text
validated_steps.md
```

Entrada relevante:

```text
2026-04-25 - Frontend-driven HUB user alta with Beaver provisioning validated
```

Secuencia ya validada:

1. `GET /tenants/`
2. `GET /tenants/{tenant_id}/beaver/roles`
3. `POST /auth/user`
4. `POST /users/{user_id}/tenants`
5. `POST /users/{user_id}/tenants/{tenant_id}/beaver/provision`
6. `GET /auth/users`
7. `GET /users/{user_id}/tenants`

Resultado validado:

- usuario creado en HUB;
- membresia creada en HUB con `beaver_role_id`;
- usuario creado en Beaver;
- rol Beaver asociado;
- no se necesita endpoint compuesto nuevo para esta fase;
- el frontend ya puede ejecutar el alta real.

## Punto de partida funcional

Ahora que el usuario normal existe en HUB y Beaver, el siguiente paso es:

```text
si el usuario NO es superadmin en HUB, redirigirlo a su Beaver usando el bridge
```

El bridge Beaver ya fue implementado y probado en el backend Spring Boot de Beaver IoT.

Endpoint Beaver validado:

```http
POST /api/v1/hub/session/exchange
```

Este endpoint intercambia un JWT handoff firmado por el HUB por tokens Beaver:

- `access_token`
- `refresh_token`
- `token_type`
- `expires_in`

Ejemplo de respuesta exitosa ya observado:

```json
{
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "expires_in": 86377
  },
  "status": "Success",
  "request_id": "..."
}
```

## Regla de negocio objetivo

Despues del login en HUB:

- si `is_superadmin = true`:
  - el usuario entra al dashboard/admin del HUB;
  - no se redirige a Beaver automaticamente.
- si `is_superadmin = false`:
  - el HUB debe resolver el tenant del usuario;
  - el HUB debe generar un handoff token firmado;
  - el frontend debe usar ese handoff para entrar en Beaver;
  - Beaver debe emitir sus propios tokens;
  - el usuario termina en la URL Beaver del tenant.

## Precondiciones del bridge Beaver

El bridge Beaver espera que:

- el tenant exista en Beaver;
- el usuario exista en Beaver;
- el usuario este habilitado en Beaver;
- el usuario pertenezca al tenant correcto;
- el JWT handoff sea valido;
- el JWT no este expirado;
- el `jti` no haya sido usado antes.

Estas precondiciones ya quedan cubiertas para nuevos usuarios porque el alta validada provisiona Beaver antes del login/redirect.

## Archivos/documentos que se deben leer antes de tocar nada

### Backend HUB

```text
validated_steps.md
alta-hub-back.md
beaver_hubbing_runbook.md
discovered_info.md
app/routes/auth.py
app/routes/user_tenants.py
app/routes/tenants.py
app/models/user.py
app/models/user_tenant.py
app/models/tenant.py
app/models/tenant_domain.py
app/core/config.py
app/core/security.py
app/core/deps.py
```

### Frontend HUB

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront\beaver_frontend_alignment_runbook.md
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront\src\pages\Login.js
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront\src\api\auth.js
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront\src\api\user.js
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront\src\pages\Users.js
```

### Beaver backend

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\bridge_testing.md
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\beaver-back-bridge-spec-v2.md
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\hub-bridge-implementation-log.md
```

Si hace falta revisar codigo Beaver:

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\services\authentication\authentication-service
```

Clases esperables a buscar:

```text
HubSessionExchangeController
HubSessionExchangeService
HubHandoffTokenValidator
HubTokenReplayProtectionService
BeaverOAuth2TokenIssuer
BeaverTokenResponseFactory
HubHandoffTokenClaims
```

## Contrato Beaver bridge ya conocido

Endpoint:

```http
POST /api/v1/hub/session/exchange
```

Body:

```json
{
  "code": "<hub_handoff_jwt>"
}
```

Configuracion Beaver esperada:

```text
HUB_BRIDGE_ENABLED=true
HUB_BRIDGE_ISSUER=http://hub.local.test
HUB_BRIDGE_AUDIENCE=beaver-hub-bridge
HUB_BRIDGE_PUBLIC_KEY=<public-key-one-line-base64-or-pem>
HUB_BRIDGE_MAX_CLOCK_SKEW=30s
HUB_BRIDGE_MAX_TOKEN_AGE=120s
```

Claims esperados o recomendados en el JWT handoff:

```json
{
  "iss": "http://hub.local.test",
  "aud": "beaver-hub-bridge",
  "sub": "3",
  "jti": "uuid",
  "iat": 1777100000,
  "nbf": 1777100000,
  "exp": 1777100120,
  "purpose": "beaver_web_handoff",
  "email": "user@example.com",
  "tenant_id": "default",
  "hub_user_id": 3,
  "hub_tenant_id": 1,
  "nickname": "user1"
}
```

Importante:

- `tenant_id` en el JWT debe ser el tenant id real que Beaver espera.
- En pruebas actuales Beaver usa tenant `"default"`.
- El HUB `tenant_id` numerico no tiene por que coincidir con el `tenant_id` de Beaver.
- Si no existe un campo dedicado de mapping HUB tenant -> Beaver tenant, hay que decidir donde guardarlo o como derivarlo.

## Riesgo importante: mapping de tenant HUB vs tenant Beaver

Actualmente el modelo HUB `Tenant` tiene:

- `id`
- `code`
- `name`
- `redirect_url`
- `beaver_base_url`
- `beaver_admin_username`
- `beaver_admin_password_encrypted`

Pero el bridge Beaver valida `tenant_id` contra el tenant de Beaver.

Pregunta clave:

```text
Que valor debe poner el HUB en el claim `tenant_id` del handoff?
```

Opciones:

1. Usar `Tenant.code` como tenant id Beaver.
2. Agregar un campo nuevo `beaver_tenant_id` a `tenants`.
3. Usar un valor fijo temporal `"default"` en local.

Recomendacion probable:

- para local, puede valer `"default"` si la instancia Beaver actual usa ese tenant;
- para diseno real, agregar `beaver_tenant_id` o documentar que `Tenant.code` debe coincidir con Beaver tenant id.

Esta decision debe cerrarse antes de implementar produccion.

## Tareas backend HUB

### Backend tarea 1 - Confirmar contrato exacto del bridge

Revisar:

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\bridge_testing.md
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot\beaver-back-bridge-spec-v2.md
```

Confirmar:

- issuer exacto;
- audience exacto;
- purpose exacto;
- claims obligatorios;
- formato de public key aceptado;
- TTL recomendado;
- si `sub` debe ser email, user id HUB o cualquier identificador estable;
- si `tenant_id` debe ser string `"default"` en local.

### Backend tarea 2 - Configuracion HUB para firmar handoff

Agregar configuracion en backend HUB.

Variables sugeridas:

```text
HUB_BRIDGE_ISSUER=http://hub.local.test
HUB_BRIDGE_AUDIENCE=beaver-hub-bridge
HUB_BRIDGE_PRIVATE_KEY=<private-key-or-path>
HUB_BRIDGE_TOKEN_TTL_SECONDS=120
HUB_BRIDGE_PURPOSE=beaver_web_handoff
```

Decidir si private key se guarda:

- como valor PEM/base64 en `.env`;
- como path a fichero local;
- como secret manager en despliegue futuro.

Para local:

- preferible usar path o PEM en `.env`;
- no commitear claves reales.

Archivo probable:

```text
app/core/config.py
```

### Backend tarea 3 - Crear helper de JWT handoff

Archivo sugerido:

```text
app/core/hub_bridge.py
```

Responsabilidades:

- cargar private key;
- generar `jti`;
- generar `iat`, `nbf`, `exp`;
- firmar JWT RS256;
- devolver token string.

Dependencias posibles:

- `pyjwt`
- `cryptography`

Revisar `requirements.txt` antes de agregar dependencias.

No meter logica HTTP en este helper.

### Backend tarea 4 - Crear endpoint handoff para frontend

Endpoint sugerido:

```http
POST /auth/beaver-handoff
```

Alternativas:

```http
POST /auth/handoff/beaver
POST /auth/beaver/session
```

Recomendacion:

- usar `POST /auth/beaver-handoff` por claridad y menor impacto.

Autorizacion:

- requiere usuario autenticado HUB;
- si usuario es `superadmin`, probablemente devolver 400 o 403 porque superadmin no usa redirect automatico;
- si usuario normal, resolver su tenant/membresia.

Request body posible:

Opcion A, sin body:

```json
{}
```

El backend usa el `tenant_id` del token HUB actual.

Opcion B, con tenant explicito:

```json
{
  "tenant_id": 1
}
```

Recomendacion:

- para primera fase, aceptar body opcional con `tenant_id`;
- si no viene, usar `tenant_id` del JWT HUB;
- validar que el usuario tiene membresia activa con ese tenant.

Response sugerida:

```json
{
  "redirect_url": "http://localhost:9000",
  "beaver_base_url": "http://localhost",
  "exchange_url": "http://localhost/api/v1/hub/session/exchange",
  "code": "<hub_handoff_jwt>",
  "expires_in": 120,
  "tenant_id": 1,
  "beaver_tenant_id": "default"
}
```

Importante:

- `code` es el JWT handoff.
- `exchange_url` apunta al backend/API Beaver, no necesariamente al frontend Beaver.
- `redirect_url` apunta al frontend Beaver.

### Backend tarea 5 - Resolver tenant y usuario para handoff

Usar:

```text
app/core/deps.py
app/models/user.py
app/models/user_tenant.py
app/models/tenant.py
```

Reglas:

- el usuario debe existir y estar activo;
- el usuario no debe ser superadmin para redirect automatico;
- la membresia debe existir;
- la membresia debe estar activa;
- el tenant debe existir y estar activo;
- el tenant debe tener `redirect_url`;
- el tenant debe tener `beaver_base_url`;
- resolver `beaver_tenant_id` o equivalente.

Si el usuario tiene varias membresias:

- si viene `tenant_id` en request, usar esa;
- si no viene y el token actual tiene `tenant_id`, usar esa;
- si aun asi hay varias posibles, devolver error claro para que frontend pida seleccion.

### Backend tarea 6 - No tocar provision ni alta

No cambiar:

```text
POST /auth/user
POST /users/{user_id}/tenants
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Estos ya estan validados.

### Backend tarea 7 - Verificacion backend

Validaciones minimas:

```powershell
python -m compileall app
```

Si se agregan dependencias, probar import real.

Prueba manual sugerida con Swagger/curl:

1. login HUB como usuario normal;
2. llamar `POST /auth/beaver-handoff`;
3. tomar `code`;
4. llamar Beaver:

```http
POST http://localhost/api/v1/hub/session/exchange
```

Body:

```json
{
  "code": "<hub_handoff_jwt>"
}
```

Resultado esperado:

- `200`;
- `access_token`;
- `refresh_token`;
- `token_type = Bearer`.

## Tareas frontend HUB

### Frontend tarea 1 - Revisar login actual

Archivo:

```text
src/pages/Login.js
```

Revisar:

- que hace despues de `login`;
- como llama a `/auth/me`;
- como decide si el usuario es superadmin;
- a donde navega si es superadmin;
- que hace si no es superadmin actualmente.

### Frontend tarea 2 - Crear cliente API handoff

Archivo sugerido:

```text
src/api/beaverHandoff.js
```

Funcion:

```js
export async function createBeaverHandoff(token, tenantId) {
  // POST /auth/beaver-handoff
}
```

Request:

```json
{
  "tenant_id": 1
}
```

O sin body si backend lo permite.

Response esperada:

```json
{
  "redirect_url": "http://localhost:9000",
  "beaver_base_url": "http://localhost",
  "exchange_url": "http://localhost/api/v1/hub/session/exchange",
  "code": "...",
  "expires_in": 120,
  "tenant_id": 1,
  "beaver_tenant_id": "default"
}
```

### Frontend tarea 3 - Decidir estrategia de entrega del code a Beaver

Hay dos opciones.

#### Opcion A - Frontend HUB llama al exchange y guarda tokens Beaver

Flujo:

1. HUB frontend llama `POST /auth/beaver-handoff`.
2. HUB frontend llama `POST {exchange_url}` con `{ code }`.
3. Beaver devuelve tokens.
4. HUB frontend redirige a `redirect_url` intentando transportar tokens.

Problema:

- hay que saber como Beaver Web espera recibir tokens;
- puede requerir localStorage/cookie/formato interno del frontend Beaver;
- es mas acoplado al frontend Beaver.

#### Opcion B - Redirigir a una ruta puente en Beaver Web

Flujo:

1. HUB frontend obtiene `code`.
2. HUB frontend redirige a:

```text
{redirect_url}/hub-bridge?code=<jwt>
```

3. Beaver Web lee `code`.
4. Beaver Web llama a su propio backend:

```http
POST /api/v1/hub/session/exchange
```

5. Beaver Web guarda tokens como en login normal.

Problema:

- requiere una pequeña ruta/pagina en Beaver frontend;
- pero es probablemente la arquitectura mas limpia.

Pendiente:

- confirmar si Beaver Web ya tiene una ruta puente o si hay que crearla.

### Frontend tarea 4 - Implementar redireccion para no-superadmin

Regla:

- si `userData.is_superadmin` es true:
  - mantener flujo actual al HUB;
- si false:
  - llamar a handoff;
  - redirigir segun estrategia elegida.

Debe mostrar errores claros:

- usuario sin membresia activa;
- tenant sin `redirect_url`;
- tenant sin configuracion Beaver;
- handoff fallido;
- exchange fallido.

### Frontend tarea 5 - Verificacion frontend

Validar:

1. login superadmin:
   - sigue entrando al HUB;
   - no llama handoff.
2. login usuario normal:
   - llama `/auth/login`;
   - llama `/auth/me` si aplica;
   - llama `/auth/beaver-handoff`;
   - redirige a Beaver o ejecuta exchange;
   - termina con sesion Beaver.

## Posibles tareas en Beaver frontend

Solo si se elige la opcion B.

Proyecto probable:

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot-web
```

Tarea:

- crear ruta tipo:

```text
/hub-bridge?code=...
```

Responsabilidad:

1. leer query param `code`;
2. llamar:

```http
POST /api/v1/hub/session/exchange
```

3. guardar tokens igual que login normal;
4. redirigir al dashboard Beaver.

Antes de implementar:

- revisar como Beaver Web guarda tokens normales;
- revisar cliente HTTP/API de Beaver Web;
- revisar rutas existentes.

## Preguntas abiertas que hay que cerrar

### 1. Que valor exacto debe llevar `tenant_id` en el JWT handoff?

Opciones:

- `"default"` temporal local;
- `Tenant.code`;
- nuevo campo `Tenant.beaver_tenant_id`.

Pregunta para humano:

```text
En la instancia Beaver actual, el tenant operativo es siempre `default` o cada tenant HUB tendra un tenant id Beaver distinto?
```

### 2. Como debe recibir Beaver Web el resultado?

Opciones:

- HUB frontend llama exchange y redirige con tokens;
- Beaver Web implementa ruta `/hub-bridge?code=...` y llama exchange.

Pregunta para humano/Codex Beaver frontend:

```text
Existe ya una ruta o mecanismo en Beaver Web para recibir un handoff code?
Si no existe, preferimos crearla?
```

### 3. Donde guardar la private key del HUB?

Opciones:

- `.env` como PEM/base64;
- path a fichero local;
- secret manager futuro.

Pregunta:

```text
Para local usamos la misma clave RSA de pruebas del bridge o generamos una nueva estable para HUB?
```

### 4. Debe `POST /auth/login` devolver ya informacion de redirect?

Opciones:

- mantener login simple y crear endpoint separado `/auth/beaver-handoff`;
- modificar login para devolver redirect metadata si no es superadmin.

Recomendacion:

- no tocar contrato de login en primera fase;
- usar endpoint separado.

### 5. Que ocurre si usuario normal tiene varias membresias activas?

Opciones:

- usar tenant resuelto por dominio actual;
- pedir seleccion al usuario;
- usar `tenant_id` del token HUB;
- bloquear con error claro si es ambiguo.

Recomendacion probable:

- si el acceso viene por dominio tenant, usar ese tenant;
- si no hay dominio o hay varias membresias, pedir seleccion.

## Estrategia recomendada para arrancar el lunes

### Paso 1 - Backend sin tocar frontend

Implementar endpoint:

```http
POST /auth/beaver-handoff
```

Con body temporal:

```json
{
  "tenant_id": 1
}
```

Generar JWT handoff con:

- `tenant_id = "default"` temporal si es lo que Beaver local espera;
- TTL 120 segundos;
- `purpose = "beaver_web_handoff"`.

Validar manualmente contra:

```http
POST http://localhost/api/v1/hub/session/exchange
```

### Paso 2 - Confirmar exchange exitoso

Antes de tocar frontend, demostrar:

- login HUB usuario normal;
- obtener handoff;
- exchange Beaver devuelve tokens.

### Paso 3 - Frontend HUB

Agregar cliente:

```text
src/api/beaverHandoff.js
```

Modificar:

```text
src/pages/Login.js
```

Solo para no-superadmin.

### Paso 4 - Decidir si hace falta Beaver Web route

Si el exchange devuelve tokens pero no hay forma limpia de entrar al frontend Beaver, crear tarea separada para Beaver Web.

## Criterios de aceptacion del bloque redirect

### Backend

- `POST /auth/beaver-handoff` existe;
- requiere autenticacion HUB;
- rechaza superadmin si se llama para redirect automatico;
- valida membresia activa;
- genera JWT RS256 aceptado por Beaver;
- devuelve metadata de redirect/exchange;
- no expone private key;
- no toca provisioning ya validado.

### Frontend HUB

- superadmin mantiene flujo actual;
- usuario normal dispara handoff;
- usuario normal termina en Beaver o en ruta puente Beaver;
- errores se muestran de forma clara.

### Beaver

- `/api/v1/hub/session/exchange` acepta el JWT del HUB real;
- devuelve tokens Beaver;
- rechaza replay si se reutiliza el mismo token;
- rechaza tenant/email incorrectos.

## No hacer de momento

- No cambiar alta/provisioning ya validado.
- No crear endpoint compuesto de alta.
- No guardar password de usuario en HUB.
- No exponer credenciales Beaver al frontend.
- No modificar bridge Beaver si el exchange ya funciona.
- No meter tokens Beaver en logs.
- No commitear claves privadas ni HAR con credenciales.

## Comandos utiles

Backend HUB:

```powershell
cd E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack
.\venv\Scripts\uvicorn.exe main:app --reload
python -m compileall app
```

Frontend HUB:

```powershell
cd E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront
npm start
npm run build
```

Beaver Docker local, si aplica:

```powershell
cd E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\docker-local
docker compose ps
docker logs beaver-iot --tail 200
```

## Resumen ejecutivo

El alta ya esta cerrada y validada.

El lunes toca construir el puente de login:

```text
HUB login usuario normal -> HUB handoff JWT -> Beaver exchange -> Beaver session -> redirect
```

El primer entregable recomendado es backend-only:

```text
POST /auth/beaver-handoff
```

Despues se conecta el frontend HUB.

La decision mas importante antes de cerrar produccion es el mapping:

```text
HUB Tenant -> Beaver tenant_id claim
```
