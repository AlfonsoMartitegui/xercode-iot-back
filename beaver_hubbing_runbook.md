# Beaver Hubbing Runbook

## Purpose

This document defines the target approach for integrating the HUB backend with Beaver IoT instances per tenant.

The HUB is the source of truth.
Beaver acts as an operational subsystem for each tenant.

## Core Decision

User lifecycle must be controlled by the HUB.

That means:

- users are created from the HUB;
- Beaver frontend should not expose self-managed user creation;
- tenant assignment and role assignment are decided by the HUB;
- Beaver users are provisioned and maintained by the HUB.

## Functional Model

There are two different identity layers:

### 1. HUB identity

Owned by this backend.

Stores:

- internal user identity;
- username;
- email;
- password hash for HUB login;
- active/inactive state;
- tenant membership;
- HUB business role.

### 2. Beaver operational account

Owned by the Beaver instance of a specific tenant.

Stores:

- Beaver-side user account;
- Beaver-side role;
- Beaver-side user identifier if available;
- operational permissions inside Beaver.

## Integration Goal

When a user is created or updated in the HUB, the HUB must be able to synchronize that user into the correct Beaver tenant instance.

## Beaver Tenant Integration Data

Each tenant will need technical Beaver integration settings in addition to functional tenant data.

Minimum required integration fields:

- `redirect_url`
  Frontend Beaver URL for that tenant.
- `beaver_base_url`
  Backend/API Beaver base URL for that tenant.
- `beaver_admin_username`
  Technical admin account used by the HUB.
- `beaver_admin_password_encrypted`
  Encrypted technical password used by the HUB.

Potential additional fields:

- `beaver_client_id`
- `beaver_client_secret`
- `beaver_token_path`
- `beaver_sync_enabled`
- `beaver_api_version`

## Confirmed Beaver Flow

Based on current collected information, the HUB should use this flow:

1. resolve tenant from HUB logic;
2. get `beaver_base_url` and Beaver technical credentials for that tenant;
3. authenticate against Beaver:
   - `POST /oauth2/token`
4. obtain `access_token`;
5. resolve the Beaver target role;
6. create user through:
   - `POST /user/members`
7. persist synchronization result in HUB database.

## Why `/user/members` and not `/user/register`

The HUB should use Beaver administrative creation, not public/self-service registration.

Preferred endpoint:

- `POST /user/members`

Avoid as primary provisioning path:

- `POST /user/register`

Reason:

- the HUB must control tenant, role and lifecycle;
- self-registration does not fit the centralized control model.

## Proposed Synchronization Flow

### Create user

1. HUB receives user creation request.
2. HUB validates actor permissions.
3. HUB validates target tenant.
4. HUB stores user internally.
5. HUB resolves Beaver integration config of that tenant.
6. HUB authenticates against Beaver using technical tenant credentials.
7. HUB resolves Beaver role mapping.
8. HUB creates the Beaver user.
9. HUB stores synchronization result and external reference.

### Update user

1. HUB updates local user data.
2. HUB determines if Beaver-side sync is needed.
3. HUB authenticates against Beaver if needed.
4. HUB updates Beaver-side user and/or role.
5. HUB stores sync result.

### Disable user

1. HUB marks user inactive locally.
2. HUB disables or removes access in Beaver.
3. HUB stores sync status and timestamp.

## Next Operational Integration Order

Based on the current validated state, the next implementation order after initial provisioning should be:

1. update Beaver user data;
2. change Beaver user password;
3. disable Beaver user access and/or remove Beaver role association;
4. only after that, automate Beaver sync triggers from normal HUB flows.

### 1. Update user

Goal:

- when HUB user identity changes, Beaver user data should be updated to match.

Expected Beaver-side focus:

- update `email` if allowed by Beaver;
- update display value used as `nickname`;
- keep HUB as the source of truth for identity fields.

### 2. Change password

Goal:

- allow HUB-driven password changes to be reflected in Beaver.

Important note:

- Beaver requires a usable clear-text password value for password update operations;
- HUB password hashing alone is not enough to reconstruct that value later.

Operational implication:

- password synchronization must happen only at flows where the new password value is explicitly available to the HUB at runtime.

### 3. Disable user access / remove role

Goal:

- when a user loses access in HUB, Beaver access must be restricted accordingly.

This should be treated as two distinct Beaver-side actions that may or may not both be needed:

- disable Beaver user account;
- remove Beaver role association.

Reason:

- some scenarios mean the user should remain in Beaver but lose a role;
- other scenarios mean the user should lose operational access entirely.

These actions should not be collapsed conceptually too early.

### 4. Automate sync triggers

Automation should come only after the previous manual or explicit flows are stable.

Important architecture rule:

- frontend may trigger HUB actions;
- frontend should not orchestrate Beaver logic directly;
- HUB backend remains the orchestration layer.

Recommended interpretation:

- frontend saves or updates data in HUB;
- frontend may call an explicit HUB action endpoint;
- HUB decides whether Beaver provisioning, update, password sync, disable, or role removal must happen.

This keeps Beaver credentials, business rules, and failure handling centralized in the backend.

## Source of Truth

The HUB must be the source of truth.

Operational rule:

- if HUB and Beaver disagree, HUB wins;
- Beaver should not be used as the master source for user lifecycle;
- any direct manual user creation in Beaver should be treated as an exception or drift.

## Recommended Persistence for Sync Tracking

The HUB should store external account linkage for each synchronized Beaver account.

Recommended data to persist:

- internal `user_id`
- `tenant_id`
- provider name, for example `beaver`
- Beaver external user identifier if available
- Beaver external username or email
- Beaver role id
- sync status
- last sync timestamp
- last sync error

This can live in a dedicated table such as:

- `user_external_accounts`
- or `user_beaver_links`

## Role Strategy

Do not make Beaver roles the primary business model.

Recommended approach:

- define roles in the HUB;
- map HUB roles to Beaver role ids.

Example:

- HUB role: `tenant_admin`
- Beaver role id: `3`

This keeps the HUB decoupled from Beaver internals.

## Password Strategy

### Business requirement

For a normal customer-facing user, it is reasonable that the same password value is used for:

- HUB login
- Beaver login

That improves user experience.

### Important security distinction

The same password value can be reused.
The same stored hash cannot simply be reused across both systems unless Beaver explicitly supports that exact format and storage contract.

Recommended interpretation:

- the user chooses one password;
- HUB stores its own hash for that password;
- Beaver stores its own password representation according to Beaver behavior.

So the functional password is the same for the end user, but storage is system-specific.

## Technical Admin Credential Storage

The HUB will need to store technical Beaver credentials per tenant.

These credentials must never be exposed to frontend clients.

### Recommendation

Store Beaver admin credentials encrypted at rest.

Suggested field:

- `beaver_admin_password_encrypted`

### Important note about encryption choice

`3DES` is not the recommended option today.

Prefer modern symmetric encryption such as:

- AES-256-GCM
- Fernet if you want a simpler application-layer implementation
- or a secret manager / KMS if infrastructure allows it

Recommendation for this project:

- if we need an application-managed first version, use a modern symmetric encryption helper;
- keep the encryption key outside the database;
- keep the key in environment variables or, later, in a dedicated secret manager.

## Recommended Code Structure

When implementation starts, avoid spreading Beaver HTTP calls across routes.

This project should adopt a service-oriented structure aligned with standard backend practices.

Target components:

- `app/services/beaver_client.py`
  Central Beaver API adapter/client.
- `app/services/beaver_user_service.py`
  Orchestrates HUB-to-Beaver provisioning.
- `app/core/beaver_crypto.py`
  Encrypt/decrypt technical Beaver secrets.

This is the preferred architecture.
Do not use a generic `utils_beaver.py` as the main design direction unless there is a very temporary bootstrap need.

## Proposed First Technical Components

### Beaver client

Responsibilities:

- login against Beaver;
- cache access token while valid;
- call Beaver administrative endpoints;
- translate Beaver API errors into HUB-friendly exceptions.

Suggested location:

- `app/services/beaver_client.py`

### Beaver credential crypto helper

Responsibilities:

- encrypt Beaver admin passwords before persistence;
- decrypt only when needed for runtime calls;
- centralize cryptographic operations in one place.

Suggested location:

- `app/core/beaver_crypto.py`

### Beaver provisioning service

Responsibilities:

- create Beaver user;
- update Beaver user;
- disable Beaver user;
- map HUB role to Beaver role id;
- persist synchronization result.

Suggested location:

- `app/services/beaver_user_service.py`

## Expected Deployment Considerations

Deployment will need:

- Beaver integration fields per tenant;
- encryption key for Beaver technical credentials;
- environment configuration for HTTP timeout/retries;
- possibly background retry support for sync failures.

## Risks

1. Beaver request payload for `POST /user/members` may vary by Beaver version.

2. Direct frontend actions in Beaver can create drift if not disabled.

3. If Beaver is temporarily unavailable, HUB user creation may succeed locally but fail remotely.

4. Technical admin credentials are highly sensitive and must be protected.

## Pending Design Decisions Before Coding

These should be confirmed before implementation:

1. Exact tenant fields for Beaver integration.
2. Exact Beaver role mapping strategy.
3. Which user identifier is canonical:
   - `email`
   - `username`
   - or both.
4. Exact behavior when HUB user creation succeeds but Beaver provisioning fails.
5. Whether Beaver sync should be synchronous, asynchronous, or retry-based.
6. How to disable user creation in Beaver frontend cleanly.

## Recommended Next Step

Before writing integration code, define a short technical contract for:

- Beaver tenant integration fields;
- Beaver role mapping;
- sync statuses;
- failure handling policy.

After that, implementation can begin safely in the HUB backend.
