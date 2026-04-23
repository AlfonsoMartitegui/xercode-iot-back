# Validated Steps

## Purpose

This document records:

- validated implementation steps;
- current technical status of the backend;
- deployment-relevant notes;
- local connection reference points.

It should be updated after each accepted change so we can review progress and prepare server deployment with less guesswork.

## Validation Log

### 2026-04-22 - Alembic bootstrap completed

Validated:

- `Alembic` is installed in the project virtual environment.
- `alembic/` structure was initialized.
- `alembic/env.py` was connected to project settings and SQLAlchemy metadata.
- automatic schema creation through `Base.metadata.create_all()` was removed from app startup.
- an initial migration was generated:
  - `alembic/versions/d53bd0e2d398_initial_schema.py`
- migration was applied successfully with `alembic upgrade head`.

Validation result:

- current Alembic revision is `d53bd0e2d398 (head)`;
- schema now contains:
  - `alembic_version`
  - `users`
  - `tenants`
  - `tenant_domains`
  - `user_tenants`

Deployment impact:

- database schema is now expected to be managed only through Alembic;
- startup should not create tables implicitly anymore;
- server deployment must include `alembic upgrade head`.

### 2026-04-22 - Default admin seed added

Validated:

- initial migration inserts one default superadmin user;
- password is stored hashed with `bcrypt` through `passlib`.

Default seed source:

- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`

Fallback values if not provided in `.env`:

- username: `admin`
- email: `admin@local.dev`
- password: `admin1234`

Important:

- this password is only acceptable as an initial local bootstrap value;
- it must be replaced before any real deployment.

### 2026-04-22 - JWT settings externalized and password hashing fixed

Validated:

- `SECRET_KEY` is now read from `.env` instead of being hardcoded in code.
- JWT algorithm and token expiration are now configurable from `.env`.
- user creation now stores `password_hash` using real hashing through `passlib`.
- user update now re-hashes passwords instead of storing plain text.

Validation result:

- security settings are centralized in `app/core/config.py`;
- `app/core/security.py` now reads JWT settings from environment-backed config;
- admin/user management endpoints no longer save plain passwords.

Deployment impact:

- server deployment must define `SECRET_KEY`;
- server deployment should explicitly define `JWT_ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES`;
- password resets or seeded users must always use the hashed flow from application code.

### 2026-04-22 - Tenant model expanded for hub behavior

Validated:

- tenant model now includes `address`, `redirect_url`, `beaver_base_url` and `updated_at`;
- tenant creation endpoint accepts the new business fields;
- tenant listing now returns the new fields;
- `GET /whoami` now exposes redirect-oriented tenant data.
- a new Alembic revision was generated and applied:
  - `alembic/versions/f03b39532183_expand_tenant_fields.py`

Validation result:

- current Alembic revision is `f03b39532183 (head)`;
- `tenants` table now contains:
  - `id`
  - `code`
  - `name`
  - `is_active`
  - `created_at`
  - `address`
  - `redirect_url`
  - `beaver_base_url`
  - `updated_at`
- `Tenant.code` is now treated as required at API level;
- tenant uniqueness checks now cover both `name` and `code`;
- current API is closer to the real hub use case of redirecting to a tenant-specific Beaver IoT instance.

Deployment impact:

- server database must run the new Alembic revision that adds tenant business fields;
- frontend integration can start consuming `redirect_url` and `beaver_base_url`.

### 2026-04-22 - Tenant CRUD completed for frontend use

Validated:

- existing endpoints were preserved:
  - `GET /tenants/`
  - `POST /tenants/`
- new tenant endpoints were added without renaming the existing ones:
  - `GET /tenants/{tenant_id}`
  - `PUT /tenants/{tenant_id}`
  - `DELETE /tenants/{tenant_id}`

Validation result:

- frontend can now list, create, fetch, update and deactivate tenants from the backend;
- `DELETE /tenants/{tenant_id}` performs a logical delete by setting `is_active = false`;
- create, update and delete tenant actions now require a superadmin user;
- read operations remain available to authenticated users.

Deployment impact:

- frontend can switch to direct tenant detail/edit screens without backend naming changes;
- production authorization policy must ensure only intended admins receive superadmin tokens.

### 2026-04-22 - Tenant domain CRUD completed for frontend use

Validated:

- domain management endpoints were added under each tenant:
  - `GET /tenants/{tenant_id}/domains`
  - `POST /tenants/{tenant_id}/domains`
  - `GET /tenants/{tenant_id}/domains/{domain_id}`
  - `PUT /tenants/{tenant_id}/domains/{domain_id}`
  - `DELETE /tenants/{tenant_id}/domains/{domain_id}`
- domain responses now include `is_primary`.
- domain input is normalized before persistence.

Validation result:

- frontend can now list, create, fetch, update and delete tenant domains;
- write actions require `superadmin`;
- read actions remain available to authenticated users;
- domains are normalized to host-style values without protocol or path;
- when a domain is marked as primary, the previous primary domain of the same tenant is unset automatically.

Deployment impact:

- frontend can manage tenant-domain mapping directly from the backend;
- reverse proxy and DNS setup should align with the normalized host values stored in `tenant_domains`.

### 2026-04-23 - Beaver model alignment preparation completed

Validated:

- `User.email` is now mandatory and globally unique.
- `User` now includes `updated_at`.
- `Tenant` now includes:
  - `beaver_admin_username`
  - `beaver_admin_password_encrypted`
- `UserTenant` now includes:
  - `beaver_role_id`
  - `updated_at`
- reversible encryption helper based on `Fernet` was added for Beaver technical credentials.
- environment-backed encryption key support was added through:
  - `BEAVER_CREDENTIALS_ENCRYPTION_KEY`
- tenant contracts were extended so:
  - `beaver_admin_username` is returned in normal responses;
  - `beaver_admin_password` is accepted as write-only input and stored encrypted;
  - encrypted Beaver tenant password is never exposed in normal GET responses.
- explicit user-tenant management endpoints were added:
  - `GET /users/{user_id}/tenants`
  - `POST /users/{user_id}/tenants`
  - `PUT /users/{user_id}/tenants/{tenant_id}`
  - `DELETE /users/{user_id}/tenants/{tenant_id}`
- existing user management flow in `auth.py` was kept intact.
- a new Alembic revision was created and applied:
  - `alembic/versions/6c90d57d8e3f_beaver_model_alignment.py`

Validation result:

- current Alembic revision is `6c90d57d8e3f (head)`;
- backend data model is now aligned with the Beaver preparation runbook for:
  - `User`
  - `Tenant`
  - `UserTenant`
- tenant API is now ready to persist Beaver technical admin credentials safely at rest;
- frontend can manage explicit tenant memberships without relying only on broad user endpoints;
- no Beaver sync/provisioning logic was introduced yet.

Deployment impact:

- server deployment must define a stable `BEAVER_CREDENTIALS_ENCRYPTION_KEY`;
- this key must not be rotated casually because stored tenant Beaver credentials would become unreadable;
- server deployment must continue running `alembic upgrade head`;
- frontend integration can start using the explicit user-tenant endpoints and Beaver tenant technical fields.

### 2026-04-23 - Beaver phase 2A technical authentication validated

Validated:

- global Beaver OAuth configuration was added through:
  - `BEAVER_CLIENT_ID`
  - `BEAVER_CLIENT_SECRET`
  - `BEAVER_HTTP_TIMEOUT_SECONDS`
- a minimal Beaver API client was introduced for technical authentication only.
- the HUB now performs Beaver login against:
  - `POST /api/v1/oauth2/token`
- a superadmin-only manual validation endpoint was added:
  - `POST /tenants/{tenant_id}/beaver/test-auth`
- the Beaver login flow now uses:
  - `Tenant.beaver_base_url`
  - `Tenant.beaver_admin_username`
  - decrypted `Tenant.beaver_admin_password_encrypted`
  - global `BEAVER_CLIENT_ID`
  - global `BEAVER_CLIENT_SECRET`
- Beaver technical authentication was tested successfully end-to-end from HUB to local Beaver Docker.

Validation result:

- the tenant Beaver backend base URL was validated as:
  - `http://localhost:9000`
- technical auth returns a valid Beaver token payload from the HUB flow;
- the HUB can now confirm Beaver connectivity and tenant technical credentials without exposing secrets;
- no Beaver user provisioning was implemented yet;
- the previously observed error `Invalid Beaver credential or encryption key` was confirmed to happen when the tenant Beaver password is written directly in the database instead of being stored through the backend encryption flow.

Operational note:

- `beaver_admin_password_encrypted` must not be written manually in clear text directly into the database;
- Beaver tenant password must be saved through the backend create/update tenant flow so it is encrypted with the current application key before runtime use.

Deployment impact:

- each tenant must store a valid Beaver backend API base URL and technical admin credentials before authentication tests can succeed;
- environment configuration must include stable Beaver OAuth client credentials shared by the managed Beaver deployments;
- local and server operations can now validate Beaver connectivity before attempting real user provisioning.

## Current Status Summary

Completed:

- migration system introduced;
- initial schema versioned;
- startup decoupled from schema creation;
- default admin bootstrap available.
- JWT secret moved to environment configuration;
- user create/update paths now hash passwords correctly.
- tenant model now includes redirect-oriented business fields.
- tenant CRUD is now available for frontend integration.
- tenant domain CRUD is now available for frontend integration.
- Beaver model-alignment preparation is completed for `User`, `Tenant`, `UserTenant` and tenant-facing API contracts.
- explicit user-tenant endpoints are now available.
- Beaver tenant technical credentials can now be stored encrypted at rest.
- Beaver technical authentication from HUB to tenant Beaver is now validated.
- manual Beaver auth verification endpoint is now available per tenant.

Pending from runbook:

- confirm the real Beaver user provisioning endpoint and payload contract;
- Beaver sync/provisioning service layer;
- retry jobs and sync-tracking model;
- frontend implementation aligned to the new contracts;
- define expanded deployment checklist for server.

## Connection Reference

Current local database connection is read from `.env`.

Reference fields:

- host: `DB_HOST`
- port: `DB_PORT`
- database: `DB_NAME`
- user: `DB_USER`
- password: `DB_PASS`
- jwt secret: `SECRET_KEY`
- jwt algorithm: `JWT_ALGORITHM`
- token expiry minutes: `ACCESS_TOKEN_EXPIRE_MINUTES`

Current local target:

- host: `127.0.0.1`
- port: `3306`
- database: `iotdb`
- user: configured in local `.env`
- password: configured in local `.env`

Note:

- do not write real database passwords in versioned markdown files;
- if we need a human-readable private credential note, create a local non-versioned ops file later.

## Admin Access Reference

Initial admin user is created by the first migration.

Reference fields:

- username variable: `DEFAULT_ADMIN_USERNAME`
- email variable: `DEFAULT_ADMIN_EMAIL`
- password variable: `DEFAULT_ADMIN_PASSWORD`

Current local defaults:

- username: `admin`
- email: `admin@local.dev`
- password: `admin1234`

Deployment note:

- change the default admin password before exposing the service outside local development.

## Commands Validated

Commands already validated in this repository:

- `.\venv\Scripts\alembic.exe init alembic`
- `.\venv\Scripts\alembic.exe revision --autogenerate -m "initial_schema"`
- `.\venv\Scripts\alembic.exe upgrade head`
- `.\venv\Scripts\alembic.exe current`
- `.\venv\Scripts\alembic.exe revision --autogenerate -m "expand_tenant_fields"`
- `.\venv\Scripts\python.exe -m compileall app main.py alembic\versions\6c90d57d8e3f_beaver_model_alignment.py`
- `.\venv\Scripts\alembic.exe upgrade head`
- `POST /tenants/{tenant_id}/beaver/test-auth`

## Deployment Notes To Expand Later

We should keep extending this section as steps are validated.

Topics still to document:

- exact server environment variables;
- startup command;
- reverse proxy expectations;
- MySQL provisioning assumptions;
- migration execution order during deployment;
- default admin password rotation procedure;
- CORS values for production;
- backup and rollback approach.
