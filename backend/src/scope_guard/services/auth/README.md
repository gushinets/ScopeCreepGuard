# Authentication services

AuthService uses the existing password/session ports and explicit UoW ownership.
Register inserts only: normalized-email duplicate precheck and PostgreSQL uniqueness
reject duplicates; no existing account is updated or given a session.
Public users remain `{id, email}`. Every API owner dependency delegates to `me`.

## Internal interfaces for ANY-781 / ANY-782

Construct `AuthTokenService(lambda: AuthUnitOfWork(database.new_uow()), Passwords(), clock)`.
The optional clock returns aware UTC datetime values. Methods:

- `issue(user_id, purpose) -> IssuedAuthToken`: purpose is `verify_email` or
  `reset_password`; `.raw` is for the email-preparation caller only, and is excluded
  from repr. `.expires_at` is creation plus exactly 24 hours.
- `inspect(user_id, purpose, raw) -> bool`: read-only; never authorizes a later write
  by itself. Exact expiry is invalid.
- `revoke(user_id, purpose)`: revokes outstanding tokens of that purpose.
- `confirm_email(user_id, raw)`: atomically records confirmation evidence, consumes
  the link and revokes the other outstanding confirmation links. Password is untouched.
- `reset_password(user_id, raw, password)`: validates existing password policy,
  hashes through PasswordPort outside the write transaction, then locks and revalidates.
  Atomically replaces password_hash, increments session_version, consumes the link
  and revokes every other outstanding reset link. No session or email verification
  is created. Invalid application raises generic `InvalidAuthToken`.

All writers lock the users row first, then read/write its tokens. Account mutation,
consumption and sibling revocation share one UoW commit; failures roll back all three.
The user lock serializes same-token and different-token requests and issuance.
Issuance linearizes at acquisition of that lock: a link issued before a reset is
revoked; an issuance acquiring the lock after reset is a new request and remains
valid. Callers must treat inspect results as advisory and always use application
methods for the final write. There is no standalone consume-and-commit interface.

Tokens use secrets.token_urlsafe(32); only lowercase SHA-256 hashes enter PostgreSQL.
Do not log raw tokens, password inputs, email URLs or IssuedAuthToken.raw, or include
these in public users, exception messages, telemetry or HTTP responses. ANY-779
owns email transport; this service does not send email or create public endpoints.

## Schema and sessions

0009_auth_tokens extends the existing users table and adds auth_tokens. Hash lookup
has a unique index; outstanding revocation has a partial (user_id, purpose) index.
Purpose, 64-character hash format, exact 24-hour lifetime, token state and nonnegative
session versions are constrained. Foreign keys restrict deletion like current
profiles; no new account cleanup/deletion behavior is introduced.

Existing accounts retain NULL email_verified_at and get
email_verification_required=false. The migration then changes the default to true
for new accounts. IDs, hashes and owned records remain intact. This task does not
block unverified accounts. ANY-781 connects access policy and confirmation routes;
ANY-782 connects password recovery routes. Both own public response/email policies.

New signed sessions carry session_version from the actual user. Verification accepts
only nonnegative JSON integers (not booleans/floats/strings/null). A genuinely absent
claim maps to zero; me loads the real user and rejects mismatches. Reset invalidates
legacy sessions too. Sign-in uses the database version. Logout still expires only
the browser cookie and does not globally increment the version.

Migration authority remains the one-shot gate; API/workers perform checks only.
Current Core mappings derive from 0009_auth_tokens_schema.json; historical catalogs
remain immutable for checks during upgrade. The current auth repository uses the separate Core users mapping and requires
0009 before auth requests. UserRow remains the frozen 0001 ORM mapping; historical
workflow tests explicitly opt into a test-only historical auth adapter. Runtime
auth never falls back to the baseline or silently assumes a missing database version.
