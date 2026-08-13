# Auth and Data Isolation Plan

## Goal

Add email/password registration and login backed by local Postgres, then isolate projects and check history by the authenticated user.

## Milestones

### 1. Database and Configuration

- Add local Postgres through Docker Compose.
- Add Drizzle schema for users, projects, and history entries.
- Add migration tooling and required environment variables.

Definition of done: the database can be started locally and migrated from a clean checkout.

Validation:

- `docker compose up -d`
- `pnpm db:migrate`

### 2. Authentication

- Add register, login, logout, and current-user endpoints.
- Store sessions in a signed httpOnly cookie.
- Require valid sessions for the app and protected API routes.

Definition of done: a user can register with email/password, log out, log back in, and blocked routes redirect to login.

Validation:

- `pnpm dev`
- Manual register/login/logout flow in the browser.

### 3. User-Owned Project Data

- Replace shared client-side project state with project/history API calls.
- Scope all project queries and writes to the authenticated user's id.
- Return 404 for project ids not owned by the current user.

Definition of done: two users cannot see or write each other's projects or history.

Validation:

- Register user A, create a project, log out.
- Register user B and verify the project list is empty.
- Directly request user A's project id as user B and verify access is denied.

## Stop-and-Fix Rule

If an auth, database, or ownership check fails, stop feature wiring and fix the failing layer before continuing.
