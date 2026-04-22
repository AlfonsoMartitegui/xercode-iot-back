# Runbook

## Objetivo

Construir este proyecto como backend hub multi-tenant para:

- autenticar usuarios desde frontend;
- resolver a qué tenant pertenece cada acceso;
- almacenar usuarios, tenants y dominios asociados;
- devolver al frontend la URL de la instancia Beaver IoT correspondiente;
- operar sobre MySQL con migraciones controladas.

## Estado actual del proyecto

Situación revisada en `2026-04-22`.

Ya existe una base inicial funcional:

- `FastAPI` como framework principal.
- `SQLAlchemy` con conexión a MySQL por `pymysql`.
- modelos para `users`, `tenants`, `tenant_domains` y `user_tenants`.
- login con JWT y resolución de tenant por cabecera `Host`.
- conexión local a MySQL operativa.
- tablas ya existentes en local.

Limitaciones detectadas:

- no existe `Alembic`;
- el esquema se crea con `Base.metadata.create_all()` al arrancar;
- `SECRET_KEY` está hardcodeada;
- creación y actualización de usuarios guardan contraseñas sin hash real;
- faltan campos clave de negocio para el tenant;
- permisos todavía poco cerrados;
- no hay tests del proyecto;
- hay deuda de compatibilidad con `Pydantic v2`.

## Visión funcional objetivo

El sistema debe permitir:

1. identificar el tenant desde el acceso del frontend;
2. autenticar al usuario dentro de su tenant;
3. validar si el usuario pertenece a ese tenant;
4. devolver datos del usuario, tenant y destino de redirección;
5. permitir administración interna de tenants, usuarios, dominios y relaciones;
6. soportar evolución de esquema de base de datos con migraciones seguras.

## Modelo funcional recomendado

### Usuario

Campos mínimos:

- `id`
- `username`
- `email`
- `password_hash`
- `is_active`
- `is_superadmin`
- `created_at`
- `updated_at`

Reglas:

- `username` único global o documentar si será único por tenant;
- `email` recomendable único global;
- contraseña siempre almacenada con hash;
- superadmin fuera de restricciones de tenant.

### Tenant

Campos mínimos recomendados:

- `id`
- `code`
- `name`
- `address`
- `redirect_url`
- `beaver_base_url`
- `is_active`
- `created_at`
- `updated_at`

Notas:

- `code` debe ser único y estable;
- `redirect_url` será la URL que usará el frontend;
- `beaver_base_url` sirve para separar la URL técnica/interna de la URL de frontend si hiciera falta.

### TenantDomain

Campos mínimos:

- `id`
- `tenant_id`
- `domain`
- `is_primary`
- `created_at`

Reglas:

- `domain` único;
- normalizar sin protocolo;
- decidir si se almacenará con o sin puerto;
- un tenant puede tener varios dominios.

### Relación UserTenant

Campos mínimos:

- `id`
- `user_id`
- `tenant_id`
- `role`
- `is_active`
- `created_at`

Reglas:

- unicidad por `user_id + tenant_id`;
- roles iniciales sugeridos: `user`, `admin`, `superadmin`.

## Plan de actuaciones

### Fase 0. Congelar criterio funcional

Objetivo:
dejar cerradas las decisiones de negocio antes de tocar modelo o API.

Tareas:

- decidir si `username` será único global o por tenant;
- decidir si el login se resolverá solo por `Host` o también por parámetro/cabecera;
- decidir si `redirect_url` y `beaver_base_url` serán el mismo dato o dos distintos;
- decidir qué operaciones serán exclusivas de `superadmin`;
- decidir si el frontend recibirá solo la URL destino o también metadata del tenant.

Entregable:

- mini especificación funcional estable para backend.

### Fase 1. Saneado técnico mínimo

Objetivo:
asegurar la base actual antes de ampliar funcionalidad.

Tareas:

- mover `SECRET_KEY` y configuración JWT a `.env`;
- revisar carga de configuración centralizada;
- eliminar credenciales hardcodeadas del código;
- corregir almacenamiento de contraseñas para usar hash real siempre;
- revisar normalización de `Host` para contemplar puertos;
- cerrar endpoints sensibles para que solo `superadmin` pueda administrar.

Entregable:

- autenticación segura mínima;
- permisos básicos corregidos.

### Fase 2. Introducir Alembic

Objetivo:
pasar de esquema implícito a migraciones versionadas.

Tareas:

- instalar y configurar `Alembic`;
- enlazar `Alembic` con metadata de SQLAlchemy;
- generar migración base inicial;
- retirar dependencia de `create_all()` en arranque;
- definir flujo de trabajo local para crear y aplicar migraciones.

Entregable:

- estructura `alembic/`;
- migración inicial reproducible;
- arranque desacoplado de creación automática de tablas.

### Fase 3. Ajustar modelo de datos al negocio

Objetivo:
alinear la base de datos con el hub multi-tenant real.

Tareas:

- ampliar tabla `tenants` con campos funcionales;
- añadir `updated_at` donde falte;
- revisar unicidades e índices;
- revisar nulabilidad de campos obligatorios;
- documentar reglas de integridad entre usuarios, tenants y dominios.

Entregable:

- modelo estable y expresivo para el dominio.

### Fase 4. Reordenar arquitectura del backend

Objetivo:
separar mejor responsabilidades para que el proyecto pueda crecer.

Tareas:

- separar esquemas Pydantic de rutas;
- introducir capa de servicios o casos de uso;
- centralizar dependencias de autenticación/autorización;
- preparar estructura para CRUDs mantenibles;
- adaptar modelos Pydantic a `Pydantic v2`.

Entregable:

- código más mantenible y menos acoplado.

### Fase 5. CRUD de administración

Objetivo:
dejar operativa la administración de usuarios y tenants.

Tareas:

- CRUD de tenants;
- CRUD de dominios por tenant;
- CRUD de usuarios;
- asignación y revocación de usuarios a tenants;
- cambio de roles por tenant;
- activación/desactivación de usuarios y tenants.

Entregable:

- API administrativa coherente y segura.

### Fase 6. Endpoint hub para frontend

Objetivo:
resolver el caso de uso principal del producto.

Tareas:

- definir endpoint de resolución del tenant actual;
- devolver identidad del usuario autenticado;
- devolver `redirect_url` o destino Beaver IoT;
- devolver permisos/rol del usuario dentro del tenant;
- contemplar casos de tenant inactivo, dominio no registrado y usuario sin acceso.

Entregable:

- contrato claro para el frontend.

### Fase 7. Testing básico obligatorio

Objetivo:
proteger el comportamiento crítico antes de seguir creciendo.

Tareas:

- tests de login correcto e incorrecto;
- tests de pertenencia usuario-tenant;
- tests de resolución por dominio;
- tests de permisos de superadmin;
- tests de creación de usuarios y tenants.

Entregable:

- suite mínima automatizada.

### Fase 8. Preparación de despliegue

Objetivo:
dejar el backend listo para entorno dockerizado y evolución posterior.

Tareas:

- definir variables de entorno necesarias;
- documentar arranque local y despliegue;
- definir estrategia de migraciones en despliegue;
- revisar CORS por entorno;
- preparar datos semilla mínimos si se necesitan.

Entregable:

- backend listo para integrarse con frontend y entorno Docker.

## Orden recomendado de ejecución

Orden estricto sugerido:

1. cerrar decisiones funcionales de Fase 0;
2. asegurar contraseñas, JWT y permisos de Fase 1;
3. meter Alembic en Fase 2;
4. evolucionar modelo en Fase 3;
5. reorganizar arquitectura en Fase 4;
6. completar CRUDs en Fase 5;
7. construir endpoint hub en Fase 6;
8. cubrir con tests en Fase 7;
9. rematar despliegue en Fase 8.

## Backlog inicial accionable

Estos son los primeros pasos concretos que recomiendo ejecutar en este repo:

- crear estructura de migraciones con Alembic;
- dejar de usar `create_all()` en `main.py`;
- mover `SECRET_KEY` a `.env`;
- corregir hash de contraseñas en creación y edición de usuarios;
- definir nuevos campos de `Tenant`;
- decidir contrato exacto del endpoint hub para frontend;
- crear primer conjunto de tests de autenticación y tenant.

## Riesgos a vigilar

- romper datos actuales al introducir migraciones;
- mezclar identidad global de usuario con pertenencia por tenant;
- resolver mal el tenant si el proxy reescribe `Host`;
- exponer operaciones de administración a usuarios no autorizados;
- acoplar demasiado backend y Beaver IoT sin una interfaz clara.

## Criterios de “mínimo viable”

Consideraremos que el backend llega a una primera versión válida cuando:

- exista migración base con Alembic;
- usuarios se creen con contraseña hasheada;
- tenants guarden su URL de redirección;
- login resuelva correctamente el tenant;
- un endpoint devuelva al frontend usuario, tenant y URL destino;
- solo superadmin pueda administrar usuarios y tenants;
- haya tests básicos pasando.

## Forma de trabajo propuesta

Trabajaremos fase a fase.

En cada iteración:

1. elegimos una tarea concreta de este runbook;
2. implementamos solo ese bloque;
3. verificamos comportamiento;
4. actualizamos el runbook si cambia el criterio.

## Siguiente paso recomendado

Empezar por esta secuencia:

1. Fase 0: cerrar decisiones mínimas del modelo funcional;
2. Fase 1: asegurar contraseñas y secretos;
3. Fase 2: incorporar Alembic.

Si mantenemos ese orden, evitaremos rehacer base de datos y endpoints dos veces.
