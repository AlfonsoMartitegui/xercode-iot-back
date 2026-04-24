# Documentos Autologin

## Objetivo

Centralizar en una sola carpeta toda la documentacion del puente HUB -> Beaver para no dispersar decisiones en demasiados `.md`.

## Documentos

### 1. Estrategia general

- [beaver_handoff_bridge_strategy.md](e:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\documentos_autologin\beaver_handoff_bridge_strategy.md:1)

Contenido:

- estrategia completa;
- flujo extremo a extremo;
- principios de seguridad;
- fases;
- degradacion y fallback.

### 2. Contrato del lado HUB

- [hub_bridge_contract.md](e:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\documentos_autologin\hub_bridge_contract.md:1)

Contenido:

- emision del `handoff token`;
- URL final de redireccion;
- claims;
- validaciones previas;
- configuracion requerida en HUB.

### 3. Modificaciones Beaver backend

- [beaver_backend_bridge_modifications.md](e:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\documentos_autologin\beaver_backend_bridge_modifications.md:1)

Contenido:

- endpoint nuevo `exchange`;
- validacion del token del HUB;
- emision de sesion Beaver;
- errores;
- persistencia de `jti`;
- configuracion necesaria.

### 4. Modificaciones Beaver web

- [beaver_web_bridge_modifications.md](e:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack\documentos_autologin\beaver_web_bridge_modifications.md:1)

Contenido:

- nueva ruta `/auth/hub-bridge`;
- lectura de `code`;
- llamada al exchange;
- guardado de `mos.token`;
- navegacion final;
- fallback a login.

## Orden Recomendado De Lectura

1. `beaver_handoff_bridge_strategy.md`
2. `hub_bridge_contract.md`
3. `beaver_backend_bridge_modifications.md`
4. `beaver_web_bridge_modifications.md`

## Decision Arquitectonica Resumida

La arquitectura elegida en estos documentos es:

- el HUB autentica;
- el HUB emite un `handoff token` corto y firmado;
- Beaver Web recibe ese token;
- Beaver backend lo valida y emite la sesion Beaver real;
- Beaver Web guarda el token en su storage habitual.

## Regla Importante

Estos documentos describen el camino recomendado para autologin sin depender de password reversible del usuario como pilar principal.
