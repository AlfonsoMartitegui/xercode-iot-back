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

### 2026-04-23 - Beaver phase 2B manual provisioning prepared and endpoint discovery documented

Validated:

- a manual Beaver provisioning flow was added for explicit superadmin use only.
- provisioning is triggered per explicit user-tenant assignment through:
  - `POST /users/{user_id}/tenants/{tenant_id}/beaver/provision`
- this manual provisioning endpoint requires a request password at call time and does not persist that password in HUB.
- Beaver provisioning flow implemented in HUB now follows:
  1. technical auth against Beaver;
  2. search Beaver user by `email`;
  3. create Beaver user if not found;
  4. search again to resolve Beaver `user_id`;
  5. associate Beaver user to `UserTenant.beaver_role_id`.
- Beaver provisioning uses:
  - HUB `User.email` as canonical external identifier;
  - HUB `User.username` as Beaver `nickname`;
  - `UserTenant.beaver_role_id` as Beaver role mapping.
- technical endpoint discovery and historical notes were documented in:
  - `discovered_info.md`

Validation result:

- phase 2B backend path is prepared with minimal scope and without changing the core HUB user-creation flow;
- HUB still does not store Beaver end-user password material;
- provisioning remains manual because Beaver requires clear-text `password` for `POST /api/v1/user/members` while HUB only stores `password_hash`;
- endpoint discovery is now preserved in repository history so future work can continue without repeating the same inspection process.

Operational note:

- `POST /api/v1/user/members` requires:
  - `email`
  - `nickname`
  - `password`
- Beaver role assignment is a separate call and is not part of user creation itself.
- if `UserTenant.beaver_role_id` is missing, manual Beaver provisioning should not proceed.

Deployment impact:

- operators can now trigger controlled Beaver provisioning without redesigning HUB password storage;
- future automation will require a deliberate password-handling strategy if provisioning is to happen automatically during normal HUB user flows;
- repository now contains a dedicated discovery record for Beaver contracts and source-level findings.

### 2026-04-23 - First real Beaver user provisioning validated

Validated:

- a real HUB user was provisioned successfully into Beaver through:
  - `POST /users/{user_id}/tenants/{tenant_id}/beaver/provision`
- the validated flow used:
  - tenant Beaver technical auth
  - Beaver user lookup by `email`
  - Beaver user creation when not found
  - Beaver role association through `UserTenant.beaver_role_id`
- the provisioning response confirmed:
  - `created_user = true`
  - `found_existing_user = false`
  - `role_associated = true`
- a real Beaver user id was returned after provisioning.

Validation result:

- the first end-to-end HUB to Beaver user provisioning flow is now validated against the local Beaver Docker deployment;
- current runtime mapping works as intended:
  - HUB `User.email` -> Beaver user lookup key
  - HUB `User.username` -> Beaver `nickname`
  - `UserTenant.beaver_role_id` -> Beaver target role
- Beaver provisioning is blocked correctly when `UserTenant.beaver_role_id` is missing.

Operational note:

- a valid Beaver role id must exist in `UserTenant.beaver_role_id` before provisioning;
- manual provisioning still requires explicit password input because HUB does not store Beaver-usable clear-text user password.

Deployment impact:

- role mapping quality is now a real operational dependency for successful Beaver provisioning;
- frontend should stop using free-text entry for `beaver_role_id` and move to a Beaver-role dropdown fed by HUB.

### 2026-04-23 - Beaver roles endpoint exposed from HUB and validated

Validated:

- a tenant-scoped HUB endpoint was added for Beaver role listing:
  - `GET /tenants/{tenant_id}/beaver/roles`
- the HUB endpoint authenticates technically against Beaver and calls:
  - `POST /api/v1/user/roles/search`
- the HUB returns a simplified frontend-friendly list with:
  - `role_id`
  - `name`
- the endpoint was validated successfully from Swagger.

Validation result:

- the frontend no longer needs to rely on manual free-text typing for `beaver_role_id`;
- the HUB now provides a clean source of truth for Beaver role selection per tenant;
- Beaver role lookup is now mediated by the HUB, keeping Beaver technical credentials out of the frontend.

Operational note:

- this endpoint should be used by frontend when rendering or editing user-tenant assignment;
- the selected dropdown option should store Beaver `role_id` into `beaver_role_id`;
- the displayed label should be the Beaver role `name`.

Deployment impact:

- frontend can now replace the free-text `beaver_role_id` input with a tenant-aware dropdown;
- HUB and frontend are now aligned for safer Beaver role mapping during user provisioning.

### 2026-04-23 - Beaver user manual update workaround prepared

Validated:

- a manual Beaver update endpoint was added:
  - `PUT /users/{user_id}/tenants/{tenant_id}/beaver/update`
- the HUB update flow now:
  1. authenticates technically against Beaver;
  2. searches Beaver user by current HUB `email`;
  3. updates Beaver user through:
     - `PUT /api/v1/user/members/{user_id}`
- the Beaver update payload uses:
  - `user_id`
  - `nickname`
  - `email`
- frontend guidance for the temporary workaround was documented in:
  - `update_beaver_user_workaround.md`

Validation result:

- HUB now has a minimal manual path to update Beaver user identity data without adding new persistence yet;
- current update behavior is intentionally limited and controlled;
- the workaround is suitable only while Beaver user lookup by current email remains valid.

Operational note:

- expected limitation: if HUB email changes first and Beaver still stores the old email, the current manual update may fail with:
  - `Beaver user not found for update`
- this is expected in the current workaround because HUB does not yet persist Beaver `user_id`;
- this limitation is documented and should be treated as known behavior, not as an unexpected regression.

Deployment impact:

- frontend can expose a manual Beaver update action when needed;
- robust update after email changes will require a later phase that persists Beaver external user identifiers in HUB.

### 2026-04-23 - Beaver role reassignment sync validated through normal HUB user-tenant update

Validated:

- `PUT /users/{user_id}/tenants/{tenant_id}` now triggers Beaver role synchronization when `beaver_role_id` changes.
- the HUB backend now attempts to:
  1. authenticate technically against Beaver;
  2. find the Beaver user by current HUB `email`;
  3. remove old Beaver role association if needed;
  4. associate the new Beaver role id.
- this flow was validated end-to-end through normal usage from:
  - HUB frontend
  - Beaver frontend

Validation result:

- the current frontend flow does not need a separate explicit action for Beaver role reassignment;
- updating `beaver_role_id` in the usual HUB user-tenant edit flow is now sufficient;
- observed behavior is correct in both systems after the change.

Operational note:

- if the Beaver user does not exist yet, local HUB update can still succeed before provisioning;
- if the Beaver user exists and is discoverable by current email, role reassignment is synchronized correctly.

Deployment impact:

- HUB and frontend are now aligned so Beaver role reassignment happens inside the normal `UserTenant` update path;
- operators no longer need to type a role id and trigger a second manual action for the common role-change case.

### 2026-04-23 - Beaver password change endpoint implemented

Validated:

- a manual Beaver password change endpoint was added:
  - `PUT /users/{user_id}/tenants/{tenant_id}/beaver/change-password`
- the HUB password-change flow now:
  1. authenticates technically against Beaver;
  2. searches Beaver user by current HUB `email`;
  3. changes Beaver password through:
     - `PUT /api/v1/user/members/{user_id}/change-password`
- the HUB endpoint accepts a minimal request body with:
  - `password`
- frontend integration guidance was documented in:
  - `change_password_beaver_workout.md`

Validation result:

- the HUB now exposes a backend-controlled Beaver password change path without exposing Beaver technical credentials to frontend;
- Beaver password alignment stays explicit and tenant-scoped instead of being hidden inside the generic HUB user update flow;
- the implementation remains consistent with the current workaround strategy already used for Beaver identity updates.

Operational note:

- frontend should first save local HUB password changes through the normal HUB user flow, then call the Beaver password endpoint only when Beaver password alignment is also required;
- the plain password is supplied only in the request and is not stored in HUB;
- this endpoint should be treated as an administrative synchronization action, not as background automatic sync.

Expected limitation:

- this flow still depends on finding the Beaver user by the current HUB `email`;
- if HUB email has changed but Beaver still stores the previous email, password change may fail with:
  - `Beaver user not found for password change`

Deployment impact:

- frontend now has a clear HUB-mediated path to align Beaver passwords when needed;
- robust password change after email divergence will require a later phase that persists Beaver external user identifiers in HUB.

### 2026-04-23 - Beaver membership disable/remove access sync implemented

Validated:

- the existing HUB membership update flow now also drives Beaver access changes through:
  - `PUT /users/{user_id}/tenants/{tenant_id}`
- the existing HUB membership delete flow now also removes Beaver access before deleting locally through:
  - `DELETE /users/{user_id}/tenants/{tenant_id}`
- no frontend contract changes were required for this phase.

Validated Beaver behavior now attached to normal membership flows:

- if `is_active` changes from `true` to `false`, HUB now desassociates the current Beaver role from that user membership;
- if `is_active` changes from `false` to `true`, HUB now reassociates the current Beaver role for that user membership;
- if the membership is deleted and it still has active Beaver role access, HUB now removes that Beaver role association before deleting the local `UserTenant` record.

Validation result:

- Beaver access management is now aligned with the existing membership lifecycle already used by frontend;
- no extra buttons or explicit frontend actions were needed for disable/remove access;
- the implementation stays minimal by reusing the existing `BeaverClient.sync_user_role(...)` behavior.

Operational note:

- if `beaver_role_id` is missing, no Beaver role synchronization is attempted;
- if the Beaver user does not exist yet, local HUB membership update or delete can still proceed because Beaver sync is skipped as a tolerable case;
- configuration, authentication, or connectivity failures against Beaver still block the operation and surface as backend errors.

Deployment impact:

- frontend membership toggle and membership delete actions are now backed by Beaver access synchronization automatically;
- the current integration remains role-association based and does not delete the Beaver user entity itself.

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
- manual Beaver user provisioning endpoint is now prepared for explicit superadmin use.
- Beaver endpoint discovery is now documented in a dedicated historical file.
- first real Beaver user provisioning has been validated end-to-end.
- Beaver role mapping is now confirmed as a required part of the provisioning workflow.
- HUB Beaver roles endpoint is now available and validated for frontend dropdown integration.
- manual Beaver user update workaround is now available and documented.
- Beaver role reassignment is now validated through the normal HUB user-tenant update flow.
- manual Beaver password change endpoint is now available and documented.
- Beaver membership disable/remove access sync is now attached to the normal `UserTenant` update and delete flows.

Pending from runbook:

- Beaver sync/provisioning service layer;
- retry jobs and sync-tracking model;
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
- `POST /users/{user_id}/tenants/{tenant_id}/beaver/provision`
- `GET /tenants/{tenant_id}/beaver/roles`
- `PUT /users/{user_id}/tenants/{tenant_id}/beaver/update`

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
