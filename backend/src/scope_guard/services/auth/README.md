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
block legacy accounts. ANY-781 enforces confirmation for new accounts;
ANY-782 connects password recovery routes.

New signed sessions carry session_version from the actual user. Verification accepts
only nonnegative JSON integers (not booleans/floats/strings/null). A genuinely absent
claim maps to zero; me loads the real user and rejects mismatches. Reset invalidates
legacy sessions too. Sign-in uses the database version. Logout still expires only
the browser cookie and does not globally increment the version.

Migration authority remains the one-shot gate; API/workers perform checks only.
Current Core mappings derive from 0010_email_confirmation_schema.json; historical catalogs
remain immutable for checks during upgrade. The current auth repository uses the separate Core users mapping and requires
0009 before auth requests. UserRow remains the frozen 0001 ORM mapping; historical
workflow tests explicitly opt into a test-only historical auth adapter. Runtime
auth never falls back to the baseline or silently assumes a missing database version.

## Email confirmation (ANY-781)

Identity and workspace access are separate. A valid signed HttpOnly session is
checked against the current database session_version. Workspace access requires
email_verified_at IS NOT NULL OR email_verification_required=false. Public users
contain only id, email and workspaceAccess (`allowed` or
`email_confirmation_required`). Current and supported legacy product dependencies
return 403 errors.emailVerificationRequired for pending identities. Identity
inspection, logout, resend and public confirmation remain reachable. Login does
not observe product activity for pending accounts.

POST /api/auth/register accepts an explicit ru/en locale (en remains the API
compatibility default). Account creation commits before token issuance and SMTP.
The 201 response carries the normal pending session even if sending fails. The
emailConfirmation envelope distinguishes accepted, failed, unknown and
not_attempted; accepted means SMTP acceptance only. Interrupted issuance/sending
is recovered by sign-in and resend, without another registration or password
change. Duplicate registration remains 409, insert-only, without a new session.

GET /api/auth/me returns the current user plus pending emailConfirmation state and
retryAfter seconds. POST /api/auth/email/resend accepts locale only; its recipient
is the authenticated account. POST /api/auth/email/confirm accepts {userId,token}
and requires no cookie. The owner comes from the link, never the current session.
It returns {ok:true} without issuing/replacing scg_session. Invalid, expired,
used, revoked and wrong-purpose links fail with errors.emailConfirmationInvalid.
The existing atomic token application and sibling revocation remain authoritative.

SCOPE_GUARD_PUBLIC_APP_URL is the trusted browser origin, not a Docker hostname or
Host/forwarded-header value. Configure it for the API; HTTPS is required in
production, local HTTP is supported in development. Absence disables production
sending without preventing non-email worker roles from starting. Link construction
uses /confirm-email#userId=...&token=.... GET never consumes a link. React submits
the token only after an explicit button action and clears the fragment on success.
It keeps refresh possible before submission without copying tokens to storage.
The application uses no-referrer and omits analytics to prevent scripts surviving
navigation into the token page. Tokens are excluded from API responses and logs.

OriginMiddleware applies to confirmation as to other mutation routes: a supplied
Origin must exactly match configured allowed_origins; absent Origin remains
supported for non-browser clients. Public confirmation exempts only session
authentication and does not grant workspace access to the submitting browser.

Migration 0010_email_confirmation adds send-attempt accounting. Reservation locks
the source advisory key first, then the user row, and atomically applies a
60-second account cooldown, 5/account/sliding hour and 30/source/sliding hour.
These numbers are implementation defaults. Failed/ambiguous/interrupted attempts
count; rejected reservations do not. Transactions end before token issuance/SMTP.
The token service rechecks pending state under its existing user lock. Resend
never revokes earlier valid links. 429 includes Retry-After; /me reconstructs
account/source cooldown after refresh. No automatic delivery retry is performed.

The source key is a domain-separated HMAC of the direct network peer; the API
Docker command disables Uvicorn proxy-header rewriting. Forwarding headers are
not trusted. Users sharing a reverse proxy/NAT therefore share the source limit;
trusted per-client proxy addressing is not introduced in this change.
