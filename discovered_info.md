# Discovered Beaver Integration Info

## Purpose

This file stores technical discoveries collected while inspecting the local Beaver deployment and its frontend codebase.

It is meant as an implementation memory aid:

- confirmed endpoints;
- observed request contracts;
- how the information was discovered;
- operational caveats for future phases.

## Discovery Method

The following techniques were used to discover Beaver contracts:

1. validate live authentication manually against the local Beaver Docker endpoint;
2. inspect Beaver frontend assets served by the local Vite dev server;
3. follow leaked source paths exposed by that dev server;
4. search the local Beaver frontend repository directly with `rg`;
5. cross-check findings with a live authenticated Beaver API request.

This was possible because the local Beaver instance exposed frontend source references such as:

- `E:/DEVELOVEMENTS/2025/XERCODE/IOT/BEAVER/beaver-iot-web/...`

## Confirmed Base Contract

- Beaver backend base URL in local validation:
  - `http://localhost:9000`
- API prefix:
  - `/api/v1`
- OAuth token endpoint:
  - `POST /api/v1/oauth2/token`

Observed OAuth request body:

```json
{
  "grant_type": "password",
  "username": "<technical-admin-username>",
  "password": "<technical-admin-password>",
  "client_id": "<global-client-id>",
  "client_secret": "<global-client-secret>"
}
```

Observed token response shape:

```json
{
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "expires_in": 86398
  },
  "status": "Success"
}
```

## Confirmed User Provisioning Flow

### 1. Administrative user creation

Confirmed endpoint:

- `POST /api/v1/user/members`

Confirmed request contract from Beaver frontend source:

```json
{
  "email": "user@example.com",
  "nickname": "User Name",
  "password": "PlainPassword123!"
}
```

Important notes:

- this contract does not include `username`;
- this contract does not include `role_id`;
- Beaver frontend types the response as `void`.

Relevant source:

- `apps/web/src/services/http/user.ts`

### 2. User search

Confirmed endpoint:

- `POST /api/v1/user/members/search`

Observed live request example:

```json
{
  "page_size": 1,
  "page_num": 1
}
```

Observed live response shape:

```json
{
  "data": {
    "page_size": 1,
    "page_number": 1,
    "total": 1,
    "content": [
      {
        "tenant_id": "default",
        "user_id": "2044116094910828545",
        "nickname": "amartitegui",
        "email": "amartitegui@amartitegui.es",
        "roles": [
          {
            "role_id": "1",
            "role_name": "super_admin"
          }
        ],
        "created_at": "1776190229828"
      }
    ]
  },
  "status": "Success"
}
```

Operational use:

- search by `email` after creation to recover the Beaver `user_id`.

### 3. User password reset

Discovered endpoint from Beaver frontend source:

- `PUT /api/v1/user/members/:user_id/change-password`

Discovered request contract:

```json
{
  "user_id": "<beaver-user-id>",
  "password": "<new-password>"
}
```

### 4. User information update

Discovered endpoint from Beaver frontend source:

- `PUT /api/v1/user/members/:user_id`

Discovered request contract:

```json
{
  "user_id": "<beaver-user-id>",
  "nickname": "Updated Name",
  "email": "updated@example.com"
}
```

Current HUB usage:

- the HUB now exposes:
  - `PUT /users/{user_id}/tenants/{tenant_id}/beaver/update`
- current HUB workaround:
  1. authenticate technically against Beaver;
  2. search Beaver user by current HUB email;
  3. if found, update Beaver user by `user_id`.

Expected limitation:

- if HUB email changes before Beaver email is updated, the current search-by-current-email approach may fail;
- in that case HUB may return:
  - `Beaver user not found for update`

Reason:

- HUB still does not persist Beaver `user_id`;
- therefore Beaver update is not yet based on a stable external identifier.

Expected future fix:

- persist Beaver `user_id` in HUB and update by that stable identifier instead of relying on current email lookup.

## Confirmed Role Association Flow

User creation and role association are separate operations.

Confirmed or strongly inferred endpoints from Beaver frontend source:

- `POST /api/v1/user/roles/:role_id/members`
- `POST /api/v1/user/roles/:role_id/undistributed-users`
- `POST /api/v1/user/roles/:role_id/associate-user`
- `POST /api/v1/user/roles/:role_id/disassociate-user`
- `POST /api/v1/user/roles/search`

Confirmed request contract for associating users to a role:

```json
{
  "role_id": "<beaver-role-id>",
  "user_ids": ["<beaver-user-id>"]
}
```

Observed valid live role-search request:

```json
{
  "page_number": 1,
  "page_size": 999
}
```

Observed valid live role-search response:

```json
{
  "data": {
    "page_size": 999,
    "page_number": 1,
    "total": 2,
    "content": [
      {
        "role_id": "2047360102588059650",
        "name": "user",
        "created_at": "1776963661491",
        "user_role_count": 0,
        "role_integration_count": 0
      },
      {
        "role_id": "1",
        "name": "super_admin",
        "created_at": "1732005490000",
        "user_role_count": 1,
        "role_integration_count": 0
      }
    ]
  },
  "status": "Success"
}
```

Observed valid live role-members request:

- `POST /api/v1/user/roles/2047360102588059650/members`

Observed response shape:

```json
{
  "data": {
    "page_size": 0,
    "page_number": 1,
    "total": 0,
    "content": []
  },
  "status": "Success"
}
```

Implication for HUB:

- `UserTenant.beaver_role_id` is the correct place to store the Beaver-side role mapping;
- provisioning should:
  1. create user if needed;
  2. recover Beaver `user_id`;
  3. associate that user to the target Beaver role.
- Beaver roles can be exposed from HUB to frontend as a tenant-scoped dropdown source.

## Confirmed HUB Mediation For Beaver Roles

The HUB now exposes a frontend-facing endpoint for Beaver roles:

- `GET /tenants/{tenant_id}/beaver/roles`

Current HUB response shape:

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

This endpoint was validated successfully from Swagger.

Practical implication:

- frontend should use this HUB endpoint to populate the Beaver role dropdown;
- frontend should stop asking users to type Beaver role ids manually;
- `beaver_role_id` should now be chosen from HUB-provided Beaver role options.

## Additional Endpoints Discovered In Beaver Frontend Source

These were discovered in the local Beaver frontend code and may be useful later:

- `POST /api/v1/user/batch-delete`
- `POST /api/v1/user/roles`
- `PUT /api/v1/user/roles/:role_id`
- `DELETE /api/v1/user/roles/:role_id`
- `POST /api/v1/user/roles/search`
- `GET /api/v1/user/menus`
- `POST /api/v1/user/roles/:role_id/associate-menu`
- `GET /api/v1/user/roles/:role_id/menus`
- `POST /api/v1/user/roles/:role_id/integrations`
- `POST /api/v1/user/roles/:role_id/disassociate-resource`
- `POST /api/v1/user/roles/:role_id/undistributed-integrations`
- `POST /api/v1/user/roles/:role_id/associate-resource`
- `POST /api/v1/user/roles/:role_id/devices`
- `POST /api/v1/user/roles/:role_id/undistributed-devices`
- `POST /api/v1/user/roles/:role_id/dashboards`
- `POST /api/v1/user/roles/:role_id/undistributed-dashboards`
- `POST /api/v1/user/members/:user_id/permission`
- `POST /api/v1/user/register`

## Confirmed Real Provisioning Runtime

The first real provisioning test from HUB to Beaver succeeded with:

- `user_id = 2`
- `tenant_id = 1`
- `email = a.martitegui.arana@gmail.com`
- `nickname = arfonzo`
- `beaver_user_id = 2047360613466869762`
- `role_id = 2047360102588059650`

Observed successful HUB response:

```json
{
  "ok": true,
  "tenant_id": 1,
  "user_id": 2,
  "email": "a.martitegui.arana@gmail.com",
  "nickname": "arfonzo",
  "beaver_user_id": "2047360613466869762",
  "created_user": true,
  "found_existing_user": false,
  "role_associated": true,
  "role_id": "2047360102588059650"
}
```

Observed failure before setting the role mapping:

- HUB returned:
  - `User-tenant Beaver role is not configured`

Implication:

- `beaver_role_id` is not optional for the current provisioning flow;
- role selection must be made easier and safer in frontend, ideally through a HUB endpoint that lists Beaver roles per tenant.

## Current Integration Interpretation

With the currently confirmed contract, the minimal Beaver provisioning sequence for HUB is:

1. authenticate technically with Beaver;
2. search Beaver user by `email`;
3. if not found, create Beaver user with:
   - `email`
   - `nickname`
   - `password`
4. search again to obtain Beaver `user_id`;
5. associate Beaver user to the role indicated by `UserTenant.beaver_role_id`.

## Known Limitation

Beaver user creation requires `password` in clear text.

The HUB currently stores only `password_hash`, not the original password.

Therefore:

- automatic provisioning using the existing HUB password store is not possible yet;
- current phase 2B uses manual provisioning with password supplied in the request and not persisted in HUB.
