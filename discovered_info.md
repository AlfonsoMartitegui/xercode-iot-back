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

## Confirmed Role Association Flow

User creation and role association are separate operations.

Confirmed or strongly inferred endpoints from Beaver frontend source:

- `POST /api/v1/user/roles/:role_id/members`
- `POST /api/v1/user/roles/:role_id/undistributed-users`
- `POST /api/v1/user/roles/:role_id/associate-user`
- `POST /api/v1/user/roles/:role_id/disassociate-user`

Confirmed request contract for associating users to a role:

```json
{
  "role_id": "<beaver-role-id>",
  "user_ids": ["<beaver-user-id>"]
}
```

Implication for HUB:

- `UserTenant.beaver_role_id` is the correct place to store the Beaver-side role mapping;
- provisioning should:
  1. create user if needed;
  2. recover Beaver `user_id`;
  3. associate that user to the target Beaver role.

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
