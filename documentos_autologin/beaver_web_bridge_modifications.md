# Beaver Web Bridge Modifications

## Objetivo

Definir de forma exacta y sin ambiguedad las modificaciones necesarias en:

- `E:\DEVELOVEMENTS\2025\XERCODE\IOT\BEAVER\beaver-iot-web`

para que Beaver Web soporte el puente de sesion emitido desde el HUB.

Este documento no implementa codigo.

## Resultado Esperado

Beaver Web debe poder:

1. recibir una redireccion desde HUB con `code`;
2. llamar a Beaver backend para hacer exchange;
3. guardar la sesion Beaver en su storage actual;
4. entrar a la app sin mostrar la pantalla de login;
5. degradar a login normal si algo falla.

## Nueva Ruta Requerida

### Ruta exacta recomendada

- `/auth/hub-bridge`

No reutilizar:

- `/auth/login`

porque mezcla dos comportamientos distintos.

## Query String Contract

### Parametro exacto

- `code`

### Ejemplo de URL

```txt
https://beaver-tenant.example.com/auth/hub-bridge?code=<hub_handoff_token>
```

### Reglas

- `code` es obligatorio para esta ruta;
- Beaver Web no debe interpretar otros parametros como token de sesion final;
- Beaver Web no debe considerar que el usuario esta autenticado solo por venir con `code`.

## Flujo Exacto En Beaver Web

### Paso 1. Entrada a la ruta

La nueva pagina `/auth/hub-bridge` debe:

- leer `code` desde query string;
- mostrar un estado visual tipo:
  - `Signing you in...`
  - o `Accediendo...`

### Paso 2. Validacion minima local

Si no existe `code`:

- navegar inmediatamente a `/auth/login`;
- opcionalmente mostrar un mensaje no tecnico.

### Paso 3. Exchange

Llamar a:

- `POST /api/v1/hub/session/exchange`

con body:

```json
{
  "code": "<hub_handoff_token>"
}
```

### Paso 4. Persistencia local del token

Si el exchange responde con exito, Beaver Web debe guardar el resultado con el mismo mecanismo que usa hoy el login normal.

El shape esperado es:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

### Regla de expiracion frontend

Beaver Web hoy convierte `expires_in` a tiempo absoluto local.

El bridge debe aplicar exactamente la misma logica que el login actual:

- `expires_in = Date.now() + 60 * 60 * 1000`

o, preferiblemente, una version consistente con lo que ya haga el login normal del frontend Beaver.

### Paso 5. Navegacion final

Tras guardar el token:

- navegar a `/`
- preferiblemente con `replace: true`

### Paso 6. Limpieza de URL

La URL final no debe conservar el `code`.

El usuario no debe quedarse en `/auth/hub-bridge?...`.

## Storage Contract

Beaver Web ya usa:

- `DEFAULT_CACHE_PREFIX = mos.`
- `TOKEN_CACHE_KEY = token`

Por tanto, el token debe seguir guardandose en:

- `localStorage["mos.token"]`

con el mismo formato que hoy usa Beaver.

## Servicio API Nuevo En Frontend

Debe existir un cliente API dedicado.

### Nombre recomendado

- `hubBridgeExchange`

### Responsabilidad

- hacer `POST /api/v1/hub/session/exchange`;
- devolver el payload `data`;
- no mezclar este flujo con `oauthLogin` normal.

## Nueva Pagina / Vista Requerida

### Nombre recomendado

- `apps/web/src/pages/auth/views/hub-bridge/index.tsx`

### Responsabilidades exactas

- leer `code`;
- llamar al exchange;
- guardar token;
- navegar a `/`;
- manejar errores controladamente.

## Estados Visuales Requeridos

### Estado 1. Loading

Texto sugerido:

- `Signing you in...`
- o `Accediendo a Beaver...`

### Estado 2. Error controlado

Texto sugerido:

- `Automatic sign-in could not be completed. Please sign in manually.`

o en espanol segun vuestro criterio.

### Regla

El error visual debe ser corto y no tecnico.

## Comportamiento En Caso De Error

Si el exchange falla:

1. borrar cualquier token parcial si se hubiera escrito;
2. opcionalmente guardar un mensaje flash temporal;
3. navegar a:
   - `/auth/login`

No debe:

- quedarse en loop;
- mostrar la app medio cargada;
- dejar un token invalido en storage;
- reintentar infinitamente.

## Casos De Error A Soportar

### Missing code

Accion:

- ir a login.

### 401 invalid token

Accion:

- ir a login;
- mostrar mensaje breve.

### 404 user not found

Accion:

- ir a login;
- mostrar mensaje breve.

### 409 replayed code

Accion:

- ir a login;
- no reintentar.

### 5xx backend unavailable

Accion:

- opcionalmente un reintento corto de una sola vez;
- si falla, ir a login.

## Cambios En Routing

Debe registrarse la nueva ruta:

- `/auth/hub-bridge`

Debe estar marcada como ruta de acceso sin login previo.

No debe requerir token Beaver previo para renderizarse.

## Cambios En BasicLayout

No hace falta redisenar `BasicLayout` si el token ya esta en storage antes de navegar a `/`.

La clave es:

- la nueva vista debe guardar correctamente el token antes de entrar a la app principal.

## Compatibilidad Con Login Normal

El flujo actual de login Beaver no debe romperse.

Deben coexistir:

- login normal por formulario;
- login bridge por `code`.

## Seguridad En Frontend

### No loguear `code`

No debe imprimirse el token/codigo en consola.

### No persistir `code`

No debe guardarse en `localStorage`, `sessionStorage` ni cookies.

### No reenviar `code` multiples veces

El cliente debe hacer un solo intento principal.

## Criterios De Aceptacion

1. Si llega una URL valida con `code`, Beaver Web entra automaticamente.
2. El token se guarda en el mismo storage que usa el login normal.
3. La app carga como si el usuario hubiese hecho login manual.
4. Si falla, el usuario termina en `/auth/login`.
5. El login manual actual sigue funcionando sin cambios funcionales.

## No Objetivos

- no cambiar el formulario actual de login;
- no sustituir `oauth2/token` para el login normal;
- no meter token Beaver por query string final;
- no depender de cookies cross-site como mecanismo principal.

## Contrato Exacto Del Lado Frontend

### Input

URL:

```txt
/auth/hub-bridge?code=<hub_handoff_token>
```

### Exchange request

```http
POST /api/v1/hub/session/exchange
Content-Type: application/json

{
  "code": "<hub_handoff_token>"
}
```

### Exchange success payload esperado

```json
{
  "status": "Success",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

### Side effects requeridos

- guardar token en `mos.token`
- navegar a `/`

### Fallback exacto

- limpiar estado parcial
- navegar a `/auth/login`
