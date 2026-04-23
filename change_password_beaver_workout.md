# Change Beaver Password Workout

## Purpose

This document explains the minimal HUB-to-Beaver password change flow and what frontend should do with it.

This is an explicit administrative action.

It is not automatic background sync.

## HUB Endpoint

Manual password change endpoint available in HUB:

- `PUT /users/{user_id}/tenants/{tenant_id}/beaver/change-password`

Request body:

```json
{
  "password": "NewPassword123!"
}
```

This endpoint:

- is `superadmin` only;
- uses the tenant technical Beaver credentials already stored in HUB;
- looks up the Beaver user by current HUB `email`;
- changes the Beaver-side password if that Beaver user is found.

## Beaver Endpoint Used By HUB

The HUB calls:

- `PUT /api/v1/user/members/{user_id}/change-password`

With payload:

```json
{
  "user_id": "<beaver-user-id>",
  "password": "<new-password>"
}
```

## Why Frontend Needs The HUB Endpoint

Frontend must not call Beaver directly for this operation because:

- Beaver access uses tenant technical admin credentials;
- those credentials must stay in backend only;
- the HUB is the orchestration layer for Beaver actions.

So frontend should call the HUB endpoint, not the Beaver endpoint.

## Recommended Frontend Flow

If the user changes local HUB password and also needs Beaver password aligned:

1. save the password change in HUB using the normal HUB user edit flow;
2. call:
   - `PUT /users/{user_id}/tenants/{tenant_id}/beaver/change-password`
3. if successful, show confirmation;
4. if Beaver lookup fails, show a clear warning.

## Expected Success Response

```json
{
  "ok": true,
  "tenant_id": 1,
  "user_id": 2,
  "email": "user@example.com",
  "beaver_user_id": "2047360613466869762",
  "password_changed": true
}
```

## Expected Limitation

This version does **not** persist Beaver `user_id` in HUB yet.

That means the flow depends on finding the Beaver user by current HUB `email`.

If HUB email changed but Beaver still stores the old email, the call may fail with:

- `Beaver user not found for password change`

## What Frontend Should Tell The User

Suggested success message:

- `Beaver password updated successfully.`

Suggested lookup failure message:

- `Beaver password could not be updated because the Beaver account was not found by the current email.`

## Summary

Current password change integration is:

- backend controlled
- explicit
- minimal
- safe for frontend consumption

Current known limitation:

- it still depends on Beaver user lookup by current email until HUB persists Beaver `user_id`
