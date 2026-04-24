# Beaver HUB Bridge Strategy

## Objetivo

Definir sin ambiguedad la estrategia para que:

- un usuario normal del HUB haga login en el HUB;
- el HUB resuelva su tenant Beaver;
- el usuario sea redirigido a la Beaver Web de ese tenant;
- Beaver Web intente crear sesion automaticamente sin pedir un segundo login manual;
- si el puente falla, Beaver Web degrade limpiamente a su pantalla de login normal.

Este documento define la estrategia completa del proceso.

## Alcance

Este flujo esta pensado para:

- usuarios normales del negocio;
- usuarios con una unica membership Beaver operativa en el contexto de acceso;
- acceso desde HUB hacia Beaver Web de la instancia del tenant.

Este flujo no cubre:

- superadmin del HUB;
- login administrativo directo en Beaver;
- federacion OAuth/OIDC estandar entre HUB y Beaver;
- login cross-browser entre dominios no confiables;
- autologin para varios tenants Beaver a la vez;
- almacenamiento reversible de password de usuario como requisito base.

## Decision Arquitectonica

La estrategia elegida es un `HUB handoff bridge`.

Eso significa:

- el HUB no intenta escribir directamente en el `localStorage` de Beaver Web;
- el HUB no redirige con el token Beaver ya metido por query string como acceso directo final;
- el HUB emite un token/codigo de traspaso corto y firmado;
- Beaver Web recibe ese token/codigo y lo entrega a Beaver backend;
- Beaver backend valida el token/codigo y genera una sesion Beaver real;
- Beaver Web guarda el token Beaver con su propio mecanismo actual y entra a la aplicacion.

## Motivo De Esta Decision

Se elige este modelo porque:

- Beaver Web ya depende de su propio `localStorage` y de su propio token;
- el HUB no puede escribir de forma segura en el `localStorage` de otro origen;
- no queremos depender de passwords reversibles de usuario como base del autologin;
- Beaver backend ya tiene servidor OAuth propio y emite tokens JWT;
- Beaver frontend ya sabe exactamente como persistir esos tokens y operar con ellos.

## Objetos Del Flujo

### 1. HUB session

Sesion normal del usuario en el HUB.

Sirve para:

- autenticar al usuario en el HUB;
- decidir su tenant;
- decidir si tiene derecho a puente hacia Beaver.

### 2. Handoff token

Token corto emitido por el HUB para una sola redireccion.

Sirve para:

- identificar al usuario;
- identificar el tenant Beaver de destino;
- demostrar que el HUB autoriza el acceso;
- evitar pedir password otra vez al usuario.

No es el token final de Beaver.

### 3. Beaver session token

Token final emitido por Beaver backend.

Sirve para:

- autenticar a Beaver Web;
- operar con APIs Beaver;
- refrescar sesion con `refresh_token`.

## Flujo Completo

### Fase 1. Login normal en HUB

1. El usuario entra al HUB.
2. El HUB autentica al usuario.
3. El HUB resuelve el tenant activo desde dominio, membership o logica de negocio.
4. El HUB comprueba si ese usuario debe entrar a Beaver.

### Fase 2. Emision de handoff

1. El HUB crea un `handoff token` firmado y de vida corta.
2. El HUB genera la URL destino Beaver Web:
   - `https://beaver-tenant.example.com/auth/hub-bridge?code=<handoff_token>`
3. El HUB redirige al navegador a esa URL.

### Fase 3. Puente en Beaver Web

1. Beaver Web abre la ruta `/auth/hub-bridge`.
2. Lee `code` desde query string.
3. Llama a Beaver backend:
   - `POST /api/v1/hub/session/exchange`
4. Si Beaver backend devuelve tokens validos:
   - Beaver Web guarda el token en su storage habitual;
   - Beaver Web navega a `/`.
5. Si el exchange falla:
   - Beaver Web limpia cualquier estado parcial;
   - Beaver Web redirige a `/auth/login`;
   - opcionalmente muestra un mensaje controlado.

### Fase 4. Sesion normal Beaver

1. Beaver Web ya tiene `access_token` y `refresh_token`.
2. `BasicLayout` detecta token y no manda a login.
3. Beaver Web funciona igual que en el flujo de login normal.

## Regla De Degradacion

El puente nunca debe dejar la app rota.

Si falla:

- el usuario debe acabar en la pantalla de login Beaver;
- no debe quedar un token parcial o corrupto en storage;
- no debe mostrarse stacktrace ni error tecnico sin controlar.

## Reglas De Seguridad

### Vida corta

El `handoff token` debe expirar muy rapido.

Recomendacion:

- `exp = now + 60 segundos`
- maximo tolerable:
  - `120 segundos`

### Un solo uso

Cada `handoff token` debe poder usarse solo una vez.

Recomendacion:

- incluir `jti`;
- almacenar `jti` como consumido tras un exchange correcto;
- rechazar reuso.

### Audience estricta

El token debe estar emitido solo para Beaver.

Recomendacion:

- `aud = beaver-hub-bridge`

### Issuer estricto

El backend Beaver debe validar quien emitio el token.

Recomendacion:

- `iss = <hub-issuer>`

### Tenant estricto

El token debe indicar explicitamente el tenant Beaver esperado.

El backend Beaver debe rechazar:

- tenant faltante;
- tenant distinto;
- usuario sin acceso a ese tenant.

### Sin password reversible obligatoria

Este flujo no debe requerir que el HUB almacene password reversible de usuario.

### Firma fuerte

El handoff token debe ir firmado por el HUB con clave privada conocida por Beaver.

Recomendacion:

- `RS256`

## Politica De Usuario

El puente debe permitirse solo si:

- el usuario existe en HUB;
- el usuario tiene membership activa para ese tenant;
- el usuario existe ya en Beaver o Beaver backend puede mapearlo correctamente;
- el usuario no es superadmin global en modo administrativo HUB si esa politica no aplica.

## Dependencia Operativa

Para que el puente funcione de verdad, el usuario debe existir ya en Beaver.

Por tanto:

- el provisioning Beaver del usuario debe ocurrir antes del primer bridge exitoso;
- si no existe el usuario Beaver, el bridge debe fallar de forma controlada y llevar a login manual o error de negocio.

## Estrategia Recomendada Por Fases

### Fase A. Redireccion controlada

Objetivo:

- tras login HUB, redirigir al `redirect_url` del tenant.

Resultado:

- el usuario llega a Beaver;
- si no hay puente todavia, Beaver pide login.

### Fase B. Bridge tecnico

Objetivo:

- anadir `handoff token` + exchange Beaver.

Resultado:

- Beaver Web puede crear sesion propia sin segundo login.

### Fase C. Hardening

Objetivo:

- un solo uso;
- auditoria;
- nonce;
- anti replay;
- trazabilidad;
- errores UI limpios.

## Criterio De Exito

Consideraremos el objetivo cumplido cuando:

1. un usuario normal haga login en HUB;
2. el HUB lo redirija a Beaver Web de su tenant;
3. Beaver Web complete el exchange;
4. el usuario entre en Beaver sin introducir credenciales otra vez.

## Criterio De Fallback Correcto

Consideraremos el fallback correcto cuando:

1. el bridge falle;
2. el usuario termine en `/auth/login` de Beaver;
3. Beaver Web siga operativa;
4. no queden tokens corruptos en storage.
