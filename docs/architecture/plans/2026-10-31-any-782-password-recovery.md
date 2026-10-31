# ANY-782 Password Recovery Implementation Plan

Approved specification: ANY-782 and comment 87749bb2, plus the implementation plan approved in the task conversation on 2026-10-31.

Goal: public password recovery through existing auth, PostgreSQL queue, dedicated email process and existing SMTP adapter. Preserve confirmation behavior and account data.

Branch: `codex/any-782-password-recovery`. Base: `codex/any-758-email-verification-password-reset`. Work only in this existing checkout. No worktrees, clones, resets, force pushes, stash removal or main merges. Preserve the untracked ANY-778 diagnosis and private files; exclude WORKLOG from commits. Do not change Linear or unrelated PRs; PR #46 remains Draft.

## Ordered implementation

- [x] Add PostgreSQL queue and rate-limit migration after actual head (currently 0010_email_confirmation); update manifest, models, revision verification and migration tests. No startup DDL or adoption bypass.
- [x] Implement atomic admission without account lookup: POST /api/auth/password/request {email,locale}, neutral 202 {ok:true}, address suppression also 202; source/global limits 429; persistence failure 503. Bound bodies to 8 KiB, email to 320 characters, tokens to 128 characters, passwords to 4096 UTF-8 bytes. Reuse registration normalization and password policy.
- [x] Add PostgreSQL counters: address cooldown 60 seconds and 3/hour, source 10/minute and 60/hour, global 100/minute and 1000/hour. Reset application: 30/source/15 minutes and 300/global/minute, counting invalid attempts. HMAC address/source keys, global admission before arbitrary counter inserts, bounded cardinality and statement/lock timeouts. Direct peer only; ignore forwarded headers and document shared proxy/NAT limits.
- [x] Implement email-only process with atomic SKIP LOCKED claim, lease UUID and 120-second expiry, commit before SMTP, fenced preparation and completion. Queue fields: purpose, recipient, nullable user, locale, state, timestamps, attempts, next attempt, lease, auth-token reference, safe failure category. Never persist plaintext reset tokens, passwords or rendered messages.
- [x] Resolve unknown users without email; send only to matching stored account email. Prepare tokens through AuthTokenService in shared UoW. On retry revoke only this job's preceding token; generate a new secret in memory. Claim recovery after crashes must handle token creation and SMTP acceptance separately. No exactly-once claim.
- [x] Bound retries to five attempts with 1/5/15/60 minute backoff plus bounded jitter; retry temporary/ambiguous, terminate rejected/invalid. SMTP deadline 30 seconds, no open DB transaction. Recovery job expires 24 hours after admission; token TTL remains 24 hours. Late stale SMTP may deliver an invalid link; never allow stale worker DB updates.
- [x] Add password_changed_at and compare job admission time under user lock before issuance. Lock order user then job. Cancel obsolete jobs after reset; no delayed fresh tokens from earlier requests.
- [x] Extend reset_password transaction: precheck token before hashing, atomically revalidate, update hash/change timestamp/session version, consume token, revoke other reset tokens and enqueue password_changed notification in same UoW before sole commit. Enqueue failure rolls back reset; later SMTP failure cannot undo commit. Preserve verification state.
- [x] Bound stored recovery jobs to 10000 and notification jobs to 1000, atomically accounting capacity. Cleanup worker batches of 500: terminal jobs after seven days, obsolete limit records after 24 hours; capacity remains bounded during worker outage. Structured logs without addresses/secrets/content.
- [x] Add public /forgot-password and /reset-password React screens, existing design and RU/EN, explicit password/confirmation submit. Fragment userId/token; GET and refresh do not consume. No browser storage or third-party scripts; no-store/no-referrer; trusted PUBLIC_APP_URL and production HTTPS. Remove fragment on success, ordinary sign-in only. Warn when another account session is open; explicit logout rather than account switching. Preserve Origin protections and update OpenAPI/client contracts.
- [x] Add email-worker authoritative Compose service and component entrypoint, reuse API image, migrate dependency, no Mailpit readiness gate. Update root/deploy composition and factual docs, Compose 2.24 compatibility and project isolation.

## Verification and acceptance

Use behavioral RED/GREEN tests for limits, queue capacity, concurrent claims/reset, lease expiry/stale completion, restart, SMTP rejection/timeout/ambiguous acceptance, bounded retries, delayed jobs, rollback and notification atomicity. Cover token expiry, malformed/wrong-owner/reused/revoked/cross-purpose cases; old password and legacy/current sessions fail after reset; account data remains intact. Cover duplicate-registration takeover for pending/verified accounts, normalized addresses and concurrent different passwords; existing confirmation regression.

Run isolated Docker/PostgreSQL tests, schema migration/gate checks, backend pytest/ruff/mypy and frontend tests/lint/types/build/contracts. Browser/Mailpit RU/EN journey includes keyboard, navigation, refresh, preview, errors and authenticated different account. Timing: randomized 500 samples per known/unknown group, worker on/off, p50/p95/p99 and bootstrap intervals; investigate repeatable median/p95 gap above max(5ms,10%).

Never start llm-worker or make LLM calls. Use documented frontend/email-worker/Mailpit components; no full-stack startup. Never reset existing databases, remove existing volumes or prune Docker. Report complete password-recovery journey, not application-wide readiness.

## Evidence, limitations and handoff

Preflight: fetch succeeded; task, remote and integration identical at 1a6d02da2270c31fe9208680f7e8cc2dacc69b38. Integration CI run 41144423262 completed successfully. Existing stash and untracked diagnosis preserved.

Record tested SHA/diff, image IDs/revision labels, fresh builds versus mounts, actual services, commands/results and remaining gaps here. Email-only recovery cannot protect a compromised mailbox; no full NIST compliance claim.

Owner: implementing agent completes remaining checkboxes, scoped commits, push and task PR targeting integration. Read actual PR head/base after creation; do not merge. Final report in Russian with evidence, limitations and PR link.


## Implementation rulings and pre-commit verification

- Preparation SQL lives in RecoveryQueue, with AuthTokenService injected for issuance; worker services remain database-independent. HTTP composition translates SQL failures in dependencies.RecoveryBoundary. Architecture boundary tests remain enforced.
- Queue capacity uses a fixed advisory transaction lock plus bounded counts rather than additional mutable capacity counters. The 11,000-row total cap bounds those counts and serializes all inserts, including atomic notification enqueue.
- Expired reset tokens also receive bounded seven-day cleanup via a partial expiry index; confirmation-token behavior is unchanged.
- ANY-782 push/PR selects a dedicated recovery CI smoke so automatic verification cannot start llm-worker. Other branch workflows retain full-stack smoke.
- Independent read-only review identified malformed Unicode and a sixth-attempt edge when more than 500 final leases expire. Both were reproduced/fixed with regression tests; final boundary review found no further concrete defect.
- Frontend: 409 tests passed (55 files), TypeScript and ESLint/boundaries passed; production build passed (existing large-chunk advisory remains).
- Backend: 914 unit/API tests passed before final boundary refactoring; 40 focused auth/recovery/migration tests passed. Final combined/full-suite checks are recorded below when complete. Ruff passed; mypy passed across 247 source files.
- Compose configuration: current 5.6.0 and checksum-verified 2.24.0 passed root/deploy/component/production synthetic configuration checks. CI contract tests: 14 passed.
- First freshly built contour: scg-any782-894fc43d64; services postgres, migrate, backend, app, email-worker, Mailpit, separate private synthetic MinIO fixture. No llm-worker, export-worker or LLM calls. No source mounts. Initial images labelled base SHA plus uncommitted scoped source; final revision-labelled rebuild follows before push.
- RU/EN HTTP/Mailpit journey passed twice: registration, durable request, recovery delivery, GET preview, reset, old-session/old-password rejection, ordinary new-password login, separate notification. Private test bucket has no public policy.
- Actual browser: sign-in link, recovery submission and neutral acknowledgement, RU/EN, refresh, malformed-link disabled form, visible keyboard focus. Reset submission and different-account explicit logout are exercised by React tests and HTTP/Mailpit automation; entering a new password through computer-use UI was not performed.
- Timing calibration: 500 known + 500 unknown addresses per phase, randomized durable admissions, synthetic limiter windows expired between batches outside measurement. Worker stopped p50 36.415/36.406ms, p95 47.630/46.391ms, p99 65.350/50.887ms; median difference bootstrap 95% interval [-0.928,0.870]ms. Worker running p50 45.573/45.594ms, p95 54.443/54.766ms, p99 60.625/59.663ms; interval [-0.982,0.853]ms. No median/p95 investigation threshold exceeded. These local distributions do not prove universal timing indistinguishability.
- Early local command failures were resolved: use the root workspace .venv (backend/.venv lacks current dependencies), run migration tests from backend, choose a new writable --basetemp under output/any782 to avoid an inaccessible pre-existing system pytest temp directory, and use unique API/integration test basenames.

Final pre-commit combined run: `../.venv/Scripts/python.exe -m pytest tests/unit tests/api tests/architecture tests/integration/test_password_recovery.py tests/integration/test_recovery_limits.py tests/integration/test_auth_tokens.py tests/integration/test_email_confirmation.py tests/integration/test_release_migration.py tests/integration/test_schema_compatibility.py tests/integration/test_migration_lock.py -q -p no:cacheprovider --basetemp=<owned output directory>` from backend: **958 passed in 164.05s**. Full frontend `vitest run`: **409 passed / 55 files**. Full backend suite is additionally running.
