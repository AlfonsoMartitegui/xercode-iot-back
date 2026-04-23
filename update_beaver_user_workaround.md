# Update Beaver User Workaround

## Purpose

This document explains the current minimal update flow for Beaver users and what frontend should do with it.

The current implementation is intentionally small and controlled.

It is a workaround phase, not the final sync model.

## Current HUB Endpoint

Manual update endpoint available in HUB:

- `PUT /users/{user_id}/tenants/{tenant_id}/beaver/update`

This endpoint:

- is `superadmin` only;
- reads current HUB values from backend;
- uses:
  - `User.email`
  - `User.username`
- updates the Beaver-side user if that Beaver user can be found.

## Current Beaver Logic

The HUB currently updates Beaver using:

1. technical auth against Beaver;
2. search Beaver user by current `email`;
3. if found, call:
   - `PUT /api/v1/user/members/{user_id}`
4. send:
   - `user_id`
   - `nickname`
   - `email`

## Important Limitation

This version does **not** persist Beaver `user_id` in HUB yet.

That means the update flow currently depends on searching Beaver by the current HUB email.

This works only when:

- the Beaver user already exists;
- the Beaver user can still be found by the same email currently stored in HUB.

## Consequence Of The Limitation

If the email has already changed in HUB but Beaver still has the old email, the current update endpoint may fail with:

- `Beaver user not found for update`

Reason:

- HUB searches Beaver using the new email;
- Beaver may still store the old one;
- without persisted `beaver_user_id`, HUB has no stable direct identifier yet.

## What Frontend Should Do Now

Frontend should treat Beaver update as a manual, explicit operation.

Recommended flow:

1. save user changes in HUB first;
2. if Beaver sync is needed, trigger:
   - `PUT /users/{user_id}/tenants/{tenant_id}/beaver/update`
3. if update succeeds, show success confirmation;
4. if update fails with “not found”, show an explicit warning that current workaround depends on matching email.

## What Frontend Should Tell The User

Suggested message for failure case:

- `Beaver user could not be found by the current email. This temporary update flow requires the Beaver account to still match the same email.`

Suggested message for success case:

- `Beaver user updated successfully.`

## Recommended Frontend UX

For now:

- do not pretend this is fully automatic background sync;
- expose it as an explicit sync/update action where needed;
- keep error handling visible and understandable.

## Why This Is Temporary

The correct next step after this workaround is:

- persist Beaver `user_id` in HUB

Once that exists, HUB will be able to:

- update Beaver user by stable external id;
- survive email changes safely;
- reduce ambiguity and failed lookups.

## Summary

Current workaround:

- simple
- backend controlled
- minimal changes
- works when Beaver user is still discoverable by current email

Not yet solved:

- robust update after HUB email changes
- persisted Beaver external identity linkage
