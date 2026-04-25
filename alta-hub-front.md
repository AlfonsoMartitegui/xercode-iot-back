# Alta de usuario HUB + membresia + provision Beaver - Frontend

## Objetivo

Definir la estrategia frontend para crear usuarios HUB, asignarles membresias tenant completas, seleccionar roles Beaver desde dropdown, y disparar provisioning Beaver usando los endpoints backend existentes.

Este documento debe servir como guia operativa para implementar o revisar el flujo en el proyecto frontend:

```text
E:\DEVELOVEMENTS\2025\XERCODE\IOT\PROYECTO\WEB_HUB\iotfront
```

## Principio principal

El frontend orquesta acciones del HUB, pero nunca llama directamente a Beaver.

El frontend debe:

- capturar datos de usuario;
- capturar una o varias membresias tenant;
- obtener roles Beaver desde el HUB;
- guardar `beaver_role_id` en la membresia;
- mandar la password al backend solo durante el alta/provisioning;
- no persistir password Beaver;
- no manejar credenciales tecnicas Beaver;
- mostrar errores claros si el provisioning falla.

## Estado frontend actual

Archivo principal:

```text
src/pages/Users.js
```

Clientes API actuales:

```text
src/api/createUser.js
src/api/editUser.js
src/api/user.js
src/api/userTenants.js
src/api/beaverRoles.js
src/api/beaverPassword.js
```

### Ya existe

Alta de usuario:

```text
src/api/createUser.js
POST /auth/user
```

Gestion de membresias:

```text
src/api/userTenants.js
GET /users/{user_id}/tenants
POST /users/{user_id}/tenants
PUT /users/{user_id}/tenants/{tenant_id}
DELETE /users/{user_id}/tenants/{tenant_id}
```

Dropdown de roles Beaver:

```text
src/api/beaverRoles.js
GET /tenants/{tenant_id}/beaver/roles
```

Cambio de password Beaver:

```text
src/api/beaverPassword.js
PUT /users/{user_id}/tenants/{tenant_id}/beaver/change-password
```

### Faltante principal

No existe cliente frontend para:

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Tampoco existe boton/flujo visual que lo invoque tras crear la membresia.

### Fisura actual

El modal de alta de usuario actual exige seleccionar tenants y envia `tenant_ids` a `POST /auth/user`.

Ese camino crea membresias basicas en backend, pero sin `beaver_role_id`.

Problema:

- luego el provisioning Beaver falla porque la membresia no tiene rol Beaver configurado;
- ademas, `tenant_ids` no sirve para futuro multi-tenant con roles distintos por tenant.

Decision frontend:

- dejar de usar el multiselect `tenantIds` como forma principal de membresia;
- reemplazarlo por membresias completas;
- cada membresia debe incluir `tenant_id`, `role`, `beaver_role_id`, `is_active`.

## Flujo final de alta propuesto

El alta debe funcionar como wizard.

Puede implementarse visualmente como:

- un modal con pasos;
- una pantalla dedicada;
- un modal largo con secciones;
- o un flujo guiado posterior al alta.

Lo importante es el orden.

### Paso 1. Datos usuario HUB

Campos:

- `username`
- `email`
- `password`
- `confirmPassword`
- `is_active`
- `is_superadmin`

Validaciones:

- `username` obligatorio;
- `email` obligatorio;
- `password` obligatorio;
- `confirmPassword` obligatorio;
- passwords deben coincidir;
- si `is_superadmin = false`, debe existir al menos una membresia;
- si `is_superadmin = true`, las membresias son opcionales y no se provisiona Beaver automaticamente.

### Paso 2. Membresias

Para usuario normal, pedir al menos una membresia.

Cada membresia debe tener:

- `tenant_id`
- `role`
- `beaver_role_id`
- `is_active`
- `provision_beaver`, implicitamente `true` en esta fase si la membresia esta activa.

Formulario por membresia:

- dropdown tenant;
- dropdown rol HUB, por ejemplo `user` / `admin`;
- dropdown rol Beaver cargado desde el tenant;
- checkbox activa.

Reglas:

- al cambiar tenant, limpiar `beaver_role_id`;
- al seleccionar tenant, cargar roles Beaver:

```http
GET /tenants/{tenant_id}/beaver/roles
```

- mostrar `role.name`;
- guardar `role.role_id` en `beaver_role_id`;
- no permitir escritura libre de `beaver_role_id`;
- si no cargan roles Beaver, impedir o advertir antes de provisionar.

### Paso 3. Crear en HUB y provisionar Beaver

Orden de llamadas:

1. Crear usuario HUB.

```http
POST /auth/user
```

Request:

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

- `tenant_ids` se envia vacio por compatibilidad con el contrato actual;
- las membresias reales se crean despues con endpoint rico.

2. Por cada membresia, crear `UserTenant`.

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

3. Por cada membresia activa, provisionar Beaver.

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Request:

```json
{
  "password": "PlainPassword123!"
}
```

4. Refrescar usuarios y membresias.

## Cliente API nuevo requerido

Crear archivo sugerido:

```text
src/api/beaverProvision.js
```

Implementacion sugerida:

```js
import axios from "axios";
import { getApiErrorMessage } from "./errors";

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:6701";

export async function provisionBeaverUser(token, userId, tenantId, password) {
  try {
    const response = await axios.post(
      `${API_URL}/users/${userId}/tenants/${tenantId}/beaver/provision`,
      { password },
      {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    return response.data;
  } catch (error) {
    throw getApiErrorMessage(
      error,
      "No se pudo provisionar el usuario en Beaver"
    );
  }
}
```

## Cambio principal en `Users.js`

Archivo:

```text
src/pages/Users.js
```

### Estado actual a modificar

Actualmente el form tiene:

```js
const [form, setForm] = useState({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
  tenantIds: [],
  is_active: true,
});
```

Problema:

- `tenantIds` expresa tenants sin rol HUB ni `beaver_role_id`.

### Estado propuesto

Sugerencia:

```js
const [form, setForm] = useState({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
  is_active: true,
  is_superadmin: false,
  memberships: [
    {
      tenant_id: "",
      role: "user",
      beaver_role_id: "",
      is_active: true,
    },
  ],
});
```

Opcional:

- permitir varias membresias en el modal;
- para primera fase, permitir solo una membresia en alta y usar la seccion existente para anadir mas despues.

Recomendacion de bajo riesgo:

- primera fase: una membresia obligatoria en alta para usuario normal;
- despues se pueden anadir mas membresias desde la seccion existente.

## Cambio en submit de alta

### Comportamiento actual

Ahora valida:

```js
if (!username || !email || !form.password || !form.confirmPassword || form.tenantIds.length === 0)
```

Y llama:

```js
await createUser(token, {
  username,
  email,
  password: form.password,
  tenant_ids: form.tenantIds,
  is_active: form.is_active,
});
```

### Comportamiento nuevo

Validar:

- usuario/email/password/confirm;
- passwords coinciden;
- si no es superadmin, hay membresia;
- si no es superadmin, membresia tiene tenant;
- si no es superadmin, membresia tiene rol HUB;
- si no es superadmin, membresia tiene rol Beaver;
- si roles Beaver no cargaron, mostrar error y no continuar.

Pseudoflujo:

```js
const createdUser = await createUser(token, {
  username,
  email,
  password: form.password,
  tenant_ids: [],
  is_active: form.is_active,
  is_superadmin: form.is_superadmin,
});

if (!form.is_superadmin) {
  for (const membership of form.memberships) {
    await createUserTenant(token, createdUser.id, {
      tenant_id: Number(membership.tenant_id),
      role: membership.role,
      beaver_role_id: membership.beaver_role_id,
      is_active: membership.is_active,
    });

    if (membership.is_active) {
      await provisionBeaverUser(
        token,
        createdUser.id,
        membership.tenant_id,
        form.password
      );
    }
  }
}

await loadUsers();
```

## Politica si falla provisioning

Si falla `createUser`:

- mostrar error;
- no seguir.

Si falla `createUserTenant`:

- el usuario puede quedar creado;
- mostrar error claro;
- refrescar lista;
- permitir anadir membresia manualmente despues.

Si falla `provisionBeaverUser`:

- no borrar usuario;
- no borrar membresia;
- mostrar mensaje:

```text
Usuario creado en HUB y membresia guardada, pero no se pudo provisionar en Beaver. Puedes reintentar.
```

- dejar visible boton para reintentar provisioning.

## Boton de reintento provisioning

Agregar en cada tarjeta de membresia un boton nuevo:

```text
Provisionar Beaver
```

O:

```text
Reintentar Beaver
```

Ubicacion recomendada:

- junto a `Guardar`, `Cambiar contrasena`, `Borrar`.

Condiciones:

- mostrar si la membresia esta activa;
- deshabilitar si falta `beaver_role_id`;
- al pulsar, pedir password en modal temporal;
- llamar a:

```http
POST /users/{user_id}/tenants/{tenant_id}/beaver/provision
```

Motivo:

- el backend no guarda password en claro;
- para reintentar la creacion Beaver hace falta password en runtime.

Modal de reintento:

- `password`
- `confirmPassword`
- boton `Provisionar Beaver`

Nota:

- puede reutilizarse estructura similar al modal actual de cambio de password Beaver;
- no mezclar semanticamente ambos botones:
  - `Provisionar Beaver` crea/asocia cuenta;
  - `Cambiar contrasena` cambia password de una cuenta ya existente.

## Dropdown de roles Beaver

Ya existe y debe conservarse.

Comportamiento requerido:

- al seleccionar tenant, cargar roles Beaver;
- mostrar loading;
- mostrar error si falla;
- mostrar mensaje si lista vacia;
- seleccionar por `role.name`;
- guardar `role.role_id` en `beaver_role_id`;
- limpiar `beaver_role_id` cuando cambia tenant.

Contrato:

```http
GET /tenants/{tenant_id}/beaver/roles
```

Response:

```json
[
  {
    "role_id": "2047360102588059650",
    "name": "user"
  },
  {
    "role_id": "1",
    "name": "super_admin"
  }
]
```

## Cambios visuales recomendados

### Modal crear usuario

Secciones:

```text
1. Datos del usuario
2. Tipo de usuario
3. Membresia inicial
4. Resultado
```

Campos:

```text
Usuario
Email
Password
Confirmar password
Activo
Superadmin
```

Si `Superadmin = true`:

- ocultar membresia inicial;
- ocultar rol Beaver;
- no provisionar Beaver.

Si `Superadmin = false`:

- mostrar membresia inicial;
- exigir tenant;
- exigir rol HUB;
- exigir rol Beaver;
- indicar que se creara la cuenta en Beaver.

Texto recomendado:

```text
La membresia define en que instancia Beaver tendra acceso este usuario.
```

```text
El rol Beaver se obtiene desde la configuracion tecnica del tenant.
```

Evitar:

```text
tenant_ids
```

```text
sync magica
```

```text
password Beaver guardada
```

## Multi-tenant futuro

El usuario puede pertenecer a varias instancias Beaver.

El frontend debe modelar esto como:

```text
1 usuario HUB -> N membresias -> N tenants Beaver
```

No como:

```text
tenant_ids: [1, 2]
```

Ejemplo conceptual:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "memberships": [
    {
      "tenant_id": 1,
      "role": "user",
      "beaver_role_id": "2047360102588059650",
      "is_active": true
    },
    {
      "tenant_id": 2,
      "role": "admin",
      "beaver_role_id": "9988776655",
      "is_active": true
    }
  ]
}
```

Para primera fase:

- permitir una membresia en alta;
- permitir anadir mas desde la seccion de membresias existente.

Para fase posterior:

- permitir varias membresias directamente en el wizard de alta;
- provisionar cada una secuencialmente;
- mostrar resultado por tenant.

## Cambios concretos por archivo

### `src/api/beaverProvision.js`

Crear archivo nuevo con `provisionBeaverUser`.

### `src/pages/Users.js`

Modificar:

- importar `provisionBeaverUser`;
- reemplazar `tenantIds` del modal por membresia inicial;
- agregar `is_superadmin` al form si no esta en UI;
- cambiar validaciones de `handleModalSubmit`;
- en create user enviar `tenant_ids: []`;
- despues crear membresia con `createUserTenant`;
- despues provisionar con `provisionBeaverUser`;
- agregar boton de reintento provisioning en cada membresia;
- agregar modal de password para provisioning/reintento, o reutilizar uno con modo separado;
- actualizar textos que dicen que no ejecuta sincronizacion con Beaver, porque tras este cambio algunas acciones si ejecutaran provisioning.

### `src/api/userTenants.js`

No necesita cambios para crear/editar/borrar membresias.

### `src/api/beaverRoles.js`

No necesita cambios si el dropdown ya funciona.

### `src/api/beaverPassword.js`

No mezclar con provisioning.

Mantenerlo como accion posterior para cambiar password de usuario ya provisionado.

## Criterios de aceptacion frontend

Alta usuario normal:

1. el formulario exige datos usuario;
2. el formulario exige tenant;
3. al elegir tenant carga roles Beaver;
4. el formulario exige rol Beaver;
5. crea usuario HUB;
6. crea membresia HUB con `beaver_role_id`;
7. provisiona Beaver con la password del alta;
8. refresca usuarios;
9. permite login/bridge posteriormente porque Beaver ya tiene usuario.

Alta superadmin:

1. permite crear sin tenant;
2. no muestra rol Beaver obligatorio;
3. no llama a provisioning Beaver.

Error provisioning:

1. muestra error claro;
2. mantiene usuario y membresia en HUB;
3. permite reintentar provisioning con password.

Membresia posterior:

1. se puede anadir nueva membresia a usuario existente;
2. selecciona rol Beaver desde dropdown;
3. permite provisionar esa nueva membresia en Beaver.

## Pruebas manuales recomendadas

### Caso 1. Usuario normal nuevo con un tenant

1. abrir Usuarios;
2. crear usuario normal;
3. elegir tenant;
4. confirmar que cargan roles Beaver;
5. elegir rol `user`;
6. crear;
7. confirmar que aparece usuario en HUB;
8. confirmar que aparece membresia con `beaver_role_id`;
9. confirmar en Beaver que el usuario existe;
10. confirmar que tiene rol asociado.

### Caso 2. Usuario normal con provisioning fallido

1. configurar tenant con credenciales Beaver incorrectas;
2. crear usuario normal;
3. confirmar error de provisioning;
4. corregir tenant;
5. usar `Reintentar Beaver`;
6. confirmar exito.

### Caso 3. Superadmin

1. crear usuario con `is_superadmin = true`;
2. no elegir tenant;
3. confirmar que no se llama a provisioning;
4. confirmar que puede entrar al HUB.

### Caso 4. Segunda membresia

1. abrir usuario existente;
2. anadir membresia en otro tenant;
3. elegir rol Beaver;
4. guardar membresia;
5. pulsar provisionar Beaver;
6. confirmar que se crea en la segunda instancia Beaver.

## Resumen ejecutivo

El frontend ya tiene la base correcta para membresias y roles Beaver.

Lo que falta es:

```text
Crear usuario -> crear membresia rica -> provisionar Beaver
```

Y dejar de usar `tenantIds` como atajo principal.

El tenant no se ignora: se modela mejor mediante `user_tenants`, que es lo correcto para soportar multiples instancias Beaver por usuario.
