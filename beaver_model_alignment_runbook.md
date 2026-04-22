# Beaver Model Alignment Runbook

## Purpose

This runbook defines the concrete model and endpoint alignment work that should happen before implementing Beaver business logic.

Goal:

- align backend models with the future Beaver integration;
- keep frontend and backend in sync;
- avoid introducing Beaver logic before the data model is ready.

## Scope Of This Runbook

This runbook focuses on:

1. `User`
2. `Tenant`
3. `UserTenant`
4. explicit frontend-facing user-tenant endpoints
5. technical decision on encryption for Beaver tenant admin credentials

This runbook does not yet implement:

- real Beaver API synchronization;
- retry jobs;
- external sync tracking model;
- disabling user creation in Beaver frontend.

## Locked Decisions

The following decisions are now considered fixed for the next implementation phase:

- `email` must be mandatory;
- `email` must be globally unique;
- `username` must remain globally unique;
- `beaver_role_id` will be stored for now;
- the HUB remains the source of truth;
- Beaver tenant technical admin password must be stored encrypted at rest;
- the encryption key must live in `.env`;
- that encryption key must be treated as stable infrastructure configuration and must not be rotated casually.

## Encryption Decision

### Objective

The HUB must store Beaver tenant technical backend credentials in a way that allows later decryption for API calls.

This is not password hashing.
This is reversible encryption.

### Recommendation

Use modern symmetric encryption at application level.

Recommended option:

- Fernet-based encryption as the first implementation

Reason:

- simpler and safer than inventing a custom crypto layer;
- well suited for encrypt/decrypt application secrets;
- more appropriate than `3DES`.

### Explicit rejection

Do not use:

- `3DES`

Reason:

- outdated;
- weaker than modern alternatives;
- not the right standard choice for a new system.

### Key storage

The encryption key must live in `.env`.

Suggested variable:

- `BEAVER_CREDENTIALS_ENCRYPTION_KEY`

### Important operational rule

This key cannot be changed casually.

Reason:

- existing encrypted Beaver credentials in the database would become unreadable;
- the HUB would lose the ability to authenticate against tenant Beaver backends.

### Operational implication

If key rotation is ever needed in the future, it must be treated as a controlled migration:

1. decrypt existing values with old key;
2. re-encrypt with new key;
3. deploy application using the new key;
4. validate all tenant credentials again.

This is not a normal config change.

## Checklist Of Planned Changes

Below is the implementation checklist in practical format:

- model
- change
- migration impact
- endpoint impact
- frontend impact

## 1. User

### Model

- `User`

### Changes

Keep:

- `id`
- `username`
- `email`
- `password_hash`
- `is_active`
- `is_superadmin`
- `created_at`

Add or change:

- `email` -> `nullable=False`
- `email` -> `unique=True`
- index on `email`
- `updated_at`

### Migration impact

- alter `users.email` to be mandatory;
- add uniqueness constraint for `email`;
- add email index if needed;
- add `updated_at`.

### Endpoint impact

Affected endpoints:

- user creation endpoint
- user update endpoint
- user listing / retrieval response models

Required behavior:

- reject missing `email`;
- reject duplicate `email`;
- reject duplicate `username`.

### Frontend impact

- user create form must require `email`;
- user edit form must validate `email`;
- duplicate email errors must be handled clearly.

## 2. Tenant

### Model

- `Tenant`

### Changes

Keep:

- `id`
- `code`
- `name`
- `address`
- `redirect_url`
- `beaver_base_url`
- `is_active`
- `created_at`
- `updated_at`

Add:

- `beaver_admin_username`
- `beaver_admin_password_encrypted`

Possible later additions, not required yet:

- `beaver_client_id`
- `beaver_client_secret`
- `beaver_sync_enabled`

### Migration impact

- add technical Beaver integration columns to `tenants`.

### Endpoint impact

Affected endpoints:

- `POST /tenants/`
- `PUT /tenants/{tenant_id}`
- `GET /tenants/`
- `GET /tenants/{tenant_id}`

Important response rule:

- do not expose `beaver_admin_password_encrypted` in normal GET responses.

Recommended request behavior:

- frontend can send Beaver technical password through a write-only field;
- backend encrypts it before persistence;
- backend never returns the encrypted value as a usable secret.

### Frontend impact

Tenant create/edit screens need a Beaver integration section with:

- Beaver backend URL
- Beaver technical admin username
- Beaver technical admin password input

Important UX note:

- stored technical password should not be shown back in clear text;
- frontend should treat it as set/reset, not read/display.

## 3. UserTenant

### Model

- `UserTenant`

### Changes

Keep:

- `id`
- `user_id`
- `tenant_id`
- `role`
- `is_active`
- `created_at`
- unique pair `user_id + tenant_id`

Add:

- `beaver_role_id`
- `updated_at`

Interpretation:

- `role` = HUB business role
- `beaver_role_id` = Beaver technical role mapping for now

### Migration impact

- add `beaver_role_id`;
- add `updated_at`.

### Endpoint impact

Affected endpoints:

- user create/update flows if they currently accept tenant assignment;
- new explicit user-tenant management endpoints.

### Frontend impact

User-tenant assignment forms must be able to send:

- `tenant_id`
- `role`
- `beaver_role_id`
- `is_active`

## 4. TenantDomain

### Model

- `TenantDomain`

### Changes

Keep as is for now:

- `id`
- `tenant_id`
- `domain`
- `is_primary`
- `created_at`

Optional later:

- `updated_at`
- `is_active`

### Migration impact

- no mandatory migration in this block.

### Endpoint impact

- none required for this specific model-alignment phase.

### Frontend impact

- none mandatory now.

## 5. Explicit User-Tenant Endpoints

### Why

Frontend needs explicit management of user membership inside tenants.

This should not remain implicit inside broad user endpoints.

### Endpoints to add or formalize

- `GET /users/{user_id}/tenants`
- `POST /users/{user_id}/tenants`
- `PUT /users/{user_id}/tenants/{tenant_id}`
- `DELETE /users/{user_id}/tenants/{tenant_id}`

### Expected payload fields

- `tenant_id`
- `role`
- `beaver_role_id`
- `is_active`

### Frontend impact

Required UI capability:

- assign a user to one or more tenants;
- edit role per tenant;
- edit Beaver role per tenant;
- activate/deactivate membership per tenant.

## 6. Data That Must Stay Out Of Scope For Now

Do not force these into current models yet:

- Beaver external user id inside `User`
- Beaver sync status inside `User`
- Beaver sync error text inside `UserTenant`
- full external account tracking in `Tenant`

These belong to a later dedicated sync-tracking model.

## Proposed Implementation Order

Recommended order:

1. update `User` model;
2. update `Tenant` model;
3. update `UserTenant` model;
4. generate Alembic migration(s);
5. update request/response schemas;
6. adjust tenant endpoints;
7. add explicit user-tenant endpoints;
8. adapt frontend forms and screens;
9. only after that, start Beaver provisioning logic.

## Delivery Checklist

This is the implementation checklist to complete later:

- [ ] `User.email` mandatory
- [ ] `User.email` unique
- [ ] `User.updated_at`
- [ ] `Tenant.beaver_admin_username`
- [ ] `Tenant.beaver_admin_password_encrypted`
- [ ] `UserTenant.beaver_role_id`
- [ ] `UserTenant.updated_at`
- [ ] encryption helper design confirmed
- [ ] encryption key variable added to `.env`
- [ ] tenant endpoints adjusted for Beaver technical fields
- [ ] explicit user-tenant endpoints created
- [ ] frontend updated to match request/response contracts

## Recommended Next Step

Once this runbook is accepted, the next coding phase should implement:

1. model changes;
2. Alembic migration;
3. endpoint contract updates;
4. frontend-alignment responses.

Only after that should the Beaver sync client/service layer begin.
