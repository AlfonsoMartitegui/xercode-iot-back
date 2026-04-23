# Beaver Roles Workout

## Purpose

This document explains the current Beaver role-selection problem and the recommended integration change for the frontend.

Right now the frontend stores `beaver_role_id` through a free-text input.

That is no longer the right UX or integration contract.

We now know that Beaver exposes real role ids and real role names, and the HUB should mediate that lookup so the frontend can use a dropdown instead of manual typing.

## Current Situation

The HUB stores Beaver role mapping in:

- `UserTenant.beaver_role_id`

This value is later used by the HUB when provisioning a Beaver user:

1. authenticate technically against Beaver;
2. create or find the Beaver user;
3. associate that Beaver user to the selected Beaver role id.

The provisioning flow has already been validated with a real Beaver role id.

That means:

- `beaver_role_id` is operationally important;
- the value must be valid;
- manual typing is fragile and error-prone.

## What We Discovered

Confirmed Beaver endpoint for listing roles:

- `POST /api/v1/user/roles/search`

Observed valid request body:

```json
{
  "page_number": 1,
  "page_size": 999
}
```

Observed response shape:

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

Confirmed useful companion endpoint:

- `POST /api/v1/user/roles/{role_id}/members`

This is useful to inspect users assigned to a Beaver role, but the main UI need for now is role listing.

## Recommended HUB Endpoint

The frontend should not call Beaver directly.

Instead, the HUB should expose a tenant-scoped endpoint such as:

- `GET /tenants/{tenant_id}/beaver/roles`

Recommended behavior:

1. validate superadmin access;
2. resolve the tenant;
3. authenticate technically against Beaver using tenant technical credentials;
4. call Beaver:
   - `POST /api/v1/user/roles/search`
5. simplify the response for frontend use.

## Recommended Response Shape

The HUB should return a simplified list like this:

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

Optional richer response:

```json
[
  {
    "role_id": "2047360102588059650",
    "name": "user",
    "user_role_count": 0
  },
  {
    "role_id": "1",
    "name": "super_admin",
    "user_role_count": 1
  }
]
```

For the first implementation, the minimal response is enough:

- `role_id`
- `name`

## Why The Frontend Should Use The HUB Endpoint

The frontend must not talk to Beaver directly for this.

Reasons:

- Beaver technical credentials belong to the tenant and are sensitive;
- the HUB already owns the Beaver auth flow;
- the HUB keeps Beaver-specific auth and request logic out of the frontend;
- the frontend only needs a clean list for a dropdown;
- if Beaver changes later, only the HUB has to adapt.

## Frontend Change Required

Current state:

- `beaver_role_id` is typed manually in an input.

Required change:

- replace that input with a dropdown/select populated from the new HUB endpoint.

## Suggested Frontend Flow

When the user opens the user-tenant assignment form:

1. detect the selected tenant;
2. call HUB:
   - `GET /tenants/{tenant_id}/beaver/roles`
3. populate a dropdown;
4. display `name`;
5. store selected `role_id` into `beaver_role_id`.

## Suggested UX

Recommended form behavior:

- label: `Beaver role`
- component: async select/dropdown
- option label: Beaver role `name`
- option value: Beaver `role_id`
- stored field in payload: `beaver_role_id`

Recommended empty/loading states:

- loading: `Loading Beaver roles...`
- empty: `No Beaver roles available for this tenant`
- error: `Could not load Beaver roles for this tenant`

## Important Validation Rules

Frontend should:

- require tenant selection before fetching roles;
- clear the selected Beaver role when tenant changes;
- not allow arbitrary free typing of `beaver_role_id`;
- allow no selection only if the business flow explicitly permits missing Beaver role mapping.

Backend should:

- reject provisioning if `beaver_role_id` is missing;
- return a clear error if Beaver auth fails or tenant Beaver config is incomplete.

## Relationship With Provisioning

This dropdown is not cosmetic.

It directly supports the validated Beaver provisioning flow:

1. user is assigned to tenant in HUB;
2. that assignment stores a valid `beaver_role_id`;
3. provisioning uses that value to call:
   - `POST /api/v1/user/roles/{role_id}/associate-user`

So this frontend change reduces operational errors and makes provisioning reliable.

## Short Implementation Recommendation

Recommended next backend endpoint:

- `GET /tenants/{tenant_id}/beaver/roles`

Recommended next frontend change:

- replace free-text `beaver_role_id` input with a tenant-aware dropdown fed by that HUB endpoint.

## Final Recommendation

Yes, the frontend should stop asking humans to type Beaver role ids manually.

The correct integration now is:

- HUB fetches Beaver roles per tenant
- frontend consumes HUB roles endpoint
- user selects Beaver role name from dropdown
- frontend stores the corresponding `role_id` in `beaver_role_id`

That is the cleanest and safest path from the current validated state.
