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

## Current Status Summary

Completed:

- migration system introduced;
- initial schema versioned;
- startup decoupled from schema creation;
- default admin bootstrap available.
- JWT secret moved to environment configuration;
- user create/update paths now hash passwords correctly.

Pending from runbook:

- restrict sensitive endpoints to superadmin where needed;
- extend tenant model with business fields;
- define deployment checklist for server.

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
