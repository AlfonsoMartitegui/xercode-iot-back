# Alta de usuario HUB + membresia + provision Beaver - Backend

## Objetivo

Definir la estrategia backend para crear usuarios en el HUB, asignarles una o varias membresias `UserTenant`, y provisionar cada membresia contra la instancia Beaver IoT correspondiente sin romper los endpoints existentes.

Este documento debe servir como guia operativa para implementar o revisar el flujo en el proyecto backend:

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\IotBack
```

## Principio principal

El HUB es la fuente de verdad.

Beaver es un subsistema operacional por tenant.

Por tanto:

- el usuario se crea primero en HUB;
- las membresias se expresan en HUB con `user_tenants`;
- cada tenant representa una instancia Beaver IoT o un destino Beaver diferenciado;
- cada membresia puede tener su propio rol HUB y su propio `beaver_role_id`;
- la provision en Beaver se hace desde backend HUB usando credenciales tecnicas del tenant;
- el frontend nunca debe llamar a Beaver directamente ni conocer credenciales tecnicas Beaver.

## Modelo conceptual

### `users`

Representa la identidad global del usuario en el HUB.

Campos relevantes actuales:

- `id`
- `username`
- `email`
- `password_hash`
- `is_active`
- `is_superadmin`
- `created_at`
- `updated_at`

Reglas:

- `username` es unico global.
- `email` es unico global.
- `password` solo llega en claro durante el request de alta o cambio de password.
- `password_hash` es lo unico que se persiste.
- un `superadmin` puede existir sin membresias tenant.

### `tenants`

Representa una instancia/destino tenant del HUB, con configuracion Beaver asociada.

Campos relevantes actuales:

- `id`
- `code`
- `name`
- `address`
- `redirect_url`
- `beaver_base_url`
- `beaver_admin_username`
- `beaver_admin_password_encrypted`
- `is_active`

Reglas:

- `beaver_base_url` es la URL backend/API de Beaver.
- `redirect_url` es la URL frontend/destino de Beaver.
- `beaver_admin_password_encrypted` es write-only desde API y nunca debe exponerse al frontend.
- la password tecnica Beaver se cifra con el helper actual de backend.

### `user_tenants`

Representa una membresia real del usuario en un tenant.

Campos actuales:

- `id`
- `user_id`
- `tenant_id`
- `role`
- `beaver_role_id`
- `is_active`
- `created_at`
- `updated_at`

Reglas:

- existe unicidad `user_id + tenant_id`;
- `role` es el rol de negocio en el HUB;
- `beaver_role_id` es el rol operacional en Beaver para esa instancia concreta;
- `beaver_role_id` puede variar por tenant;
- para provisionar en Beaver, `beaver_role_id` debe existir;
- si una membresia se desactiva o elimina, se debe retirar la asociacion de rol Beaver cuando sea posible.

## Problema con el campo legacy `tenant_ids`

El endpoint actual `POST /auth/user` acepta:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "secret",
  "is_active": true,
  "is_superadmin": false,
  "tenant_ids": [1, 2]
}
```

Actualmente ese campo crea filas en `user_tenants`, pero con una membresia incompleta:

```python
UserTenant(
    user_id=user.id,
    tenant_id=tenant.id,
    is_active=True,
    role="user"
)
```

Limitaciones:

- no permite elegir `role` por tenant;
- no permite elegir `beaver_role_id`;
- no puede expresar configuracion distinta por tenant;
- no puede controlar si se provisiona Beaver;
- no devuelve resultado de provisioning;
- deja al usuario en un estado que puede bloquear el alta Beaver por falta de `beaver_role_id`.

Decision:

- mantener `tenant_ids` por compatibilidad temporal;
- no usar `tenant_ids` como flujo principal para usuarios Beaver;
- migrar el alta funcional hacia membresias ricas basadas en `user_tenants`.

## Estado backend ya existente

### Endpoints existentes utiles

Crear usuario HUB:

```http
POST /auth/user
```

Listar membresias:

```http
GET /users/{user_id}/tenants
```

Crear membresia:

```http
POST /users/{user_id}/tenants
```

Actualizar membresia:

```http
PUT /users/{user_id}/tenants/{tenant_id}
```

Eliminar membresia:

```http
DELETE /users/{user_id}/tenants/{tenant_id}
```

Listar roles Beaver por tenant:

```http
GET /tenants/{tenant_id}/beaver/roles
```

Provisionar usuario en Beaver:

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Actualizar datos del usuario en Beaver:

```http
PUT /users/{user_id}/tenants/{tenant_id}/beaver/update
```

Cambiar password Beaver:

```http
PUT /users/{user_id}/tenants/{tenant_id}/beaver/change-password
```

### Servicio existente

Archivo:

```text
app/services/beaver_client.py
```

Responsabilidades ya implementadas:

- autenticar contra Beaver via `/oauth2/token`;
- buscar usuario Beaver por email;
- crear usuario Beaver via `/user/members`;
- asociar rol via `/user/roles/{role_id}/associate-user`;
- desasociar rol via `/user/roles/{role_id}/disassociate-user`;
- listar roles Beaver;
- actualizar usuario Beaver;
- cambiar password Beaver.

## Contrato actual de provisioning Beaver

Endpoint HUB:

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Request:

```json
{
  "password": "PlainPassword123!"
}
```

Precondiciones:

- el usuario existe en HUB;
- la membresia `user_id + tenant_id` existe;
- la membresia esta activa;
- el usuario tiene `email`;
- la membresia tiene `beaver_role_id`;
- el tenant tiene `beaver_base_url`;
- el tenant tiene `beaver_admin_username`;
- el tenant tiene `beaver_admin_password_encrypted` valido;
- las credenciales OAuth globales Beaver existen en settings.

Flujo interno:

1. cargar `User`;
2. cargar `UserTenant`;
3. cargar `Tenant`;
4. autenticar tecnicamente contra Beaver;
5. buscar usuario Beaver por `email`;
6. si no existe, llamar a Beaver:

```http
POST /user/members
```

Payload Beaver:

```json
{
  "email": "user@example.com",
  "nickname": "username",
  "password": "PlainPassword123!"
}
```

7. volver a buscar usuario por email para obtener `beaver_user_id`;
8. asociar usuario al rol:

```http
POST /user/roles/{role_id}/associate-user
```

Payload Beaver:

```json
{
  "role_id": "2047360102588059650",
  "user_ids": ["2047360613466869762"]
}
```

9. devolver resultado.

Response HUB esperada:

```json
{
  "ok": true,
  "tenant_id": 1,
  "user_id": 2,
  "email": "user@example.com",
  "nickname": "username",
  "beaver_user_id": "2047360613466869762",
  "created_user": true,
  "found_existing_user": false,
  "role_associated": true,
  "role_id": "2047360102588059650"
}
```

## Flujo backend recomendado para alta

### Fase minima, sin endpoint compuesto nuevo

El frontend orquesta contra endpoints existentes.

1. Crear usuario HUB:

```http
POST /auth/user
```

Request recomendado:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "PlainPassword123!",
  "is_active": true,
  "is_superadmin": false,
  "tenant_ids": []
}
```

Nota:

- `tenant_ids` se envia vacio para evitar crear membresias incompletas.
- Esto no significa ignorar tenants.
- Las membresias se crean en el siguiente paso mediante el endpoint rico.

2. Crear una membresia por tenant:

```http
POST /users/{user_id}/tenants
```

Request:

```json
{
  "tenant_id": 1,
  "role": "user",
  "beaver_role_id": "2047360102588059650",
  "is_active": true
}
```

3. Provisionar esa membresia en Beaver:

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Request:

```json
{
  "password": "PlainPassword123!"
}
```

4. Si hay mas tenants, repetir pasos 2 y 3 por cada tenant.

### Fase recomendada posterior: endpoint compuesto

Crear un endpoint backend nuevo para encapsular el alta completa.

Nombre sugerido:

```http
POST /auth/user-with-memberships
```

Alternativas aceptables:

```http
POST /users/full
POST /users/with-memberships
POST /admin/users
```

Contrato sugerido:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "PlainPassword123!",
  "is_active": true,
  "is_superadmin": false,
  "memberships": [
    {
      "tenant_id": 1,
      "role": "user",
      "beaver_role_id": "2047360102588059650",
      "is_active": true,
      "provision_beaver": true
    },
    {
      "tenant_id": 2,
      "role": "admin",
      "beaver_role_id": "9988776655",
      "is_active": true,
      "provision_beaver": true
    }
  ]
}
```

Reglas:

- si `is_superadmin = true`, `memberships` puede estar vacio;
- si `is_superadmin = false`, exigir al menos una membresia activa;
- si una membresia tiene `provision_beaver = true`, exigir `beaver_role_id`;
- no persistir `password` en claro;
- usar el `password` recibido solo durante la transaccion/request;
- devolver resultado detallado por membresia.

Response sugerida:

```json
{
  "ok": true,
  "user": {
    "id": 10,
    "username": "user1",
    "email": "user1@example.com",
    "is_active": true,
    "is_superadmin": false
  },
  "memberships": [
    {
      "tenant_id": 1,
      "role": "user",
      "beaver_role_id": "2047360102588059650",
      "is_active": true,
      "provision": {
        "ok": true,
        "beaver_user_id": "2047360613466869762",
        "created_user": true,
        "found_existing_user": false,
        "role_associated": true
      }
    }
  ]
}
```

## Politica de errores

### Fase minima sin sync tracking

Si falla la creacion de usuario HUB:

- no crear membresias;
- devolver error claro.

Si falla la creacion de membresia:

- el usuario HUB puede quedar creado;
- el frontend debe poder reintentar crear membresia;
- devolver error claro.

Si falla la provision Beaver:

- no borrar automaticamente usuario ni membresia;
- devolver error claro;
- permitir reintento explicito del endpoint de provisioning.

Motivo:

- borrar automaticamente puede ocultar errores y complicar soporte;
- la membresia HUB es fuente de verdad y puede quedar pendiente de provision.

### Fase futura con sync tracking

Crear tabla recomendada:

```text
user_beaver_links
```

Campos sugeridos:

- `id`
- `user_id`
- `tenant_id`
- `beaver_user_id`
- `beaver_email`
- `beaver_role_id`
- `sync_status`
- `last_sync_at`
- `last_sync_error`
- `created_at`
- `updated_at`

Estados sugeridos:

- `pending`
- `provisioned`
- `failed`
- `disabled`
- `drift`

Con esa tabla, el backend podria registrar fallos y permitir retries controlados.

## Cambios backend recomendados ahora

### 1. Validar email duplicado en `POST /auth/user`

Archivo:

```text
app/routes/auth.py
```

Problema:

- actualmente se valida `username` duplicado;
- debe validarse tambien `email` duplicado antes de escribir en DB.

Comportamiento esperado:

```json
{
  "detail": "El email ya existe"
}
```

### 2. Documentar/deprecar `tenant_ids`

Sin romper compatibilidad.

Opciones:

- dejarlo funcionando igual;
- agregar comentario claro en codigo;
- actualizar runbooks indicando que no se usa para altas Beaver.

### 3. Opcional: endurecer `POST /users/{user_id}/tenants`

Archivo:

```text
app/routes/user_tenants.py
```

Recomendacion:

- permitir `beaver_role_id = null` solo si no se pretende provisionar Beaver;
- para el flujo de alta Beaver desde frontend, la UI debe exigirlo;
- no necesariamente bloquearlo en backend todavia para no romper usos parciales.

### 4. Agregar endpoint compuesto en fase posterior

No hacerlo como primer paso si se quiere riesgo bajo.

Primero estabilizar el frontend usando endpoints existentes.

Despues crear endpoint compuesto para reducir pasos y mejorar atomicidad.

## Cambios que NO deben hacerse ahora

- No tocar el bridge Beaver.
- No llamar al endpoint Beaver `POST /user/register`.
- No exponer credenciales tecnicas Beaver al frontend.
- No guardar passwords de usuario Beaver en HUB.
- No reutilizar hashes HUB como password Beaver.
- No eliminar `tenant_ids` de golpe.
- No hacer que Beaver sea fuente de verdad de usuarios.

## Criterios de aceptacion backend

Alta usuario normal con un tenant:

1. `POST /auth/user` crea usuario HUB con password hasheada.
2. `POST /users/{user_id}/tenants` crea membresia con `beaver_role_id`.
3. `POST /users/{user_id}/tenants/{tenant_id}/beaver/provision` crea o reutiliza usuario Beaver.
4. Beaver queda con usuario asociado al rol seleccionado.
5. El bridge Beaver puede intercambiar handoff token para ese usuario porque ya existe en Beaver.

Alta usuario normal con varios tenants:

1. se crea un solo usuario HUB;
2. se crean varias filas `user_tenants`;
3. cada membresia tiene su propio `beaver_role_id`;
4. se provisiona cada tenant contra su `beaver_base_url`;
5. un fallo en un tenant no debe ocultar el estado de los demas.

Alta superadmin:

1. se crea usuario HUB con `is_superadmin = true`;
2. no se exige membresia;
3. no se provisiona Beaver automaticamente.

## Archivos backend a revisar al implementar

```text
app/routes/auth.py
app/routes/user_tenants.py
app/routes/tenants.py
app/services/beaver_client.py
app/models/user.py
app/models/user_tenant.py
app/models/tenant.py
app/core/security.py
app/core/encryption.py
```

## Resumen ejecutivo

No hay que ignorar tenants en el alta.

Hay que dejar de usar el atajo pobre `tenant_ids` como fuente de membresias Beaver y usar `user_tenants` como contrato real.

El alta correcta es:

```text
User HUB -> UserTenant rico -> Beaver provision por membresia
```

Esto soporta correctamente el futuro multi-tenant:

```text
1 usuario HUB -> N memberships -> N instancias Beaver
```
