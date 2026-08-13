# Auth and Data Isolation Test Plan

## Critical Paths

- Register a new user with a valid email and password.
- Reject invalid email, duplicate email, and short password.
- Login with the registered credentials.
- Reject an incorrect password without creating a session.
- Logout clears the session and returns to login.
- Create a project and run a scope check.
- Verify the check is saved to that user's project history.

## Isolation Checks

- User A creates a project.
- User B sees an empty project list after registering or logging in.
- User B cannot load or write history to User A's project id.
- Unauthenticated requests to protected project endpoints return unauthorized.

## Commands

- `docker compose up -d`
- `pnpm db:migrate`
- `pnpm lint`
- `pnpm build`

## Release Gate

The feature is ready when the auth flow works end to end and no project or history record can be accessed without a matching authenticated `user_id`.
