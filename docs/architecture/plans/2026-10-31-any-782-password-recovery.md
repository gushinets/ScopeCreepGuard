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


## Revision-labelled runtime evidence (2026-10-31)

Tested implementation: `dcf46494229c3d70d4b8d832b0d05227c3b83849`. The only subsequent source change is the proxy verification script's expected security headers and recovery-route coverage; production application/image sources are unchanged. Documentation/evidence updates are separate.

Fresh Docker builds (no mounted source, normal cached dependency layers permitted):

| Image | Docker image ID | OCI revision label |
|---|---|---|
| scope-guard-api:any782 (API, migrate, email-worker) | sha256:05a58d78360d1b08441ee99887e3456ddf6a5d98936257295cef3235e60e76ac | dcf46494229c3d70d4b8d832b0d05227c3b83849 |
| scope-guard-frontend:any782 | sha256:2987e147e9fa288e960aa71bf37749ce9f6a838512772e5eced40e895dc89c22 | dcf46494229c3d70d4b8d832b0d05227c3b83849 |

Commands/results:

- `docker build -f apps/api/Dockerfile --target runner --build-arg SOURCE_REVISION=dcf46494229c3d70d4b8d832b0d05227c3b83849 -t scope-guard-api:any782 .`: passed.
- Equivalent frontend runner build with the same revision label: passed.
- `python backend/scripts/verify_password_recovery.py start`: new isolated project `scg-any782-64d337452b`; PostgreSQL, migrate (exit 0), API, frontend, email-worker, Mailpit; separate private MinIO fixture. No export-worker/llm-worker. Earlier contour stopped and its database/volumes retained.
- `python backend/scripts/verify_password_recovery.py check`: passed on these images. RU/EN Mailpit journey, private bucket/no public policy, session/password revocation, ordinary login and notification, no raw tested tokens/passwords in API/proxy/worker logs.
- `python scripts/verify_react_proxy.py --image scope-guard-frontend:any782` from backend: 22 passed against the real Nginx image, including `/forgot-password`, `/reset-password`, no-store and no-referrer.
- Initial PR CI container job failed only because this proxy check still expected no-cache; the behavior change is intentional for recovery security. The updated check was reproduced red then passed locally. This does not count as a green CI claim.
- API/client contract checks, frontend lint/boundaries, Ruff and mypy passed. Current/minimum Compose configuration and 14 CI-policy tests passed.
- Actual PR #52 inspected after creation: head `codex/any-782-password-recovery`, base `codex/any-758-email-verification-password-reset` at `1a6d02da2270c31fe9208680f7e8cc2dacc69b38`. It is Draft and unmerged. PR #46 was inspected and remains Draft/unmerged. No Linear changes.

Final 2000-request calibration on revision-labelled images (500/group/phase), randomized order, durable unique-address admissions; synthetic windows expired outside measured requests:

- worker-stopped, known: n=500, p50=36.042ms, p95=49.064ms, p99=61.056ms.
- worker-stopped, unknown: n=500, p50=35.451ms, p95=47.989ms, p99=59.250ms.
- worker-stopped median difference bootstrap 95% interval: [-0.049, 1.262]ms.
- worker-running, known: n=500, p50=51.392ms, p95=66.982ms, p99=83.552ms.
- worker-running, unknown: n=500, p50=51.178ms, p95=66.711ms, p99=80.979ms.
- worker-running median difference bootstrap 95% interval: [-1.408, 1.328]ms.

No median/p95 threshold exceeded. These measurements cover this local contour and are not a proof of timing indistinguishability on every deployment. External SMTP inbox delivery remains untested. Actual browser navigation/forms/RU-EN/refresh/keyboard/error rendering was observed; explicit reset submission and already-authenticated-other-account behavior have React and HTTP/Mailpit coverage, not a computer-use password-entry claim.

Complete password-recovery journey is verified within this bounded contour; application-wide readiness is not claimed. Full generic backend pytest and GitHub CI are tracked separately until completion; do not infer their success from the focused 958-test run. Local evidence/state/logs remain under ignored output/any782; no existing volume was reset or removed, no resources pruned. The original ANY-778 untracked report and stash remain preserved.


Verification boundary correction: the optional generic full pytest collection includes production LLM-worker execution-lane tests with an injected fake provider. The local generic run was stopped rather than used as readiness evidence; its partial log and exit -1 remain in output/any782. No Docker llm-worker service or real provider API call was started. ANY-782 check-backend.sh now selects all unit/API/architecture tests plus auth/recovery/migration/Compose-config integration tests and excludes those unrelated runtime lanes. This is the same bounded contour as the completed 958-test run, plus Compose configuration. Other branches retain full pytest. Old CI runs started before this correction must not be described as the intended final contour.


Compose runtime compatibility correction: the Linux CI startup failure was reproduced with the already checksum-verified Compose 2.24 binary. All services were running, migrate exited 0, but `up --wait` rejected email-worker with `has no healthcheck configured`. Current Compose 5.6 tolerated the disabled check. Added the established worker-style database/liveness heartbeat and a 60-second marker check, independent of SMTP readiness. Lifecycle tests cover success, worker failure and database failure; all seven health/architecture checks passed after the change. Captured synthetic startup stderr/logs are retained by the harness for future failures. Minimum/current configuration checks passed; real minimum-version runtime verification follows on freshly rebuilt images.

GitHub run 41151178106 at proposed merge ff82db46d9a653353d947aac874f1f2f6cb26da2 passed backend: **959 tests**, Ruff, format (424 files), both mypy platforms and API/PDF checks. Frontend, branch-base and minimum Compose checks also passed. Container failure above was diagnosed rather than ignored. No application schema or migration gate was bypassed.


## Final heartbeat-compatible verification

Tested source revision: `2c3b1e02aee6081261c220839f8ffde4f579b6d0`; no local application changes. Subsequent commits only record evidence.

- Fresh API/email-worker image: `sha256:ba3391a1d6c1a2ceb02703a4710c2e27980765be3cf7e7dd4148978bc8201756`.
- Fresh frontend image: `sha256:05ab61439f233c51058c3e2bce426fc00f1ec96e27979b49e7b12781e09f4ed6`.
- Both OCI revision labels equal `2c3b1e02aee6081261c220839f8ffde4f579b6d0`. Actual running backend/app/email-worker IDs and labels were inspected, with empty mount lists (no source overlay).
- Actual Compose **2.24.0 runtime**, not just config: reused the owned synthetic project `scg-any782-02b735dd29`, `up -d --no-build --wait` succeeded after the health fix. PostgreSQL, backend, app, email-worker and Mailpit healthy; migrate exited 0. No schema reset or adoption bypass.
- Full RU/EN `check` passed on that minimum-version contour: HTTP request → Mailpit → non-consuming GET → reset → revoked old session/password → ordinary new-password login → notification, private synthetic bucket and secret-free tested logs. These application sources are the final sources; the earlier full timing/restart calibration remains applicable to unchanged admission/delivery transactions (heartbeat adds only a SELECT 1 every 10 seconds).
- Final local bounded suite (all unit/API/architecture plus auth/recovery/migration/schema/Compose config): **962 passed in 179.57s**. Ruff and mypy passed after the heartbeat change. Frontend application sources unchanged from the 409-test/build verification.
- Real restart evidence on the preceding source revision: durable pending jobs survived email-worker stop/restart, only a known account received mail, and request alone preserved password/session. Actual authenticated-browser navigation/refresh retained the original signed-in account on public recovery screens. New heartbeat lifecycle reviewed independently; no concrete regression found.
- Both local owned Compose contours were stopped after evidence capture. Their databases/volumes, the separate private test-storage data, and ignored output evidence are retained. No Docker prune, existing volume reset, main merge or Linear modification occurred.
- Final PR remains #52 against the agreed integration branch. CI must be read on its latest proposed merge; prior failures and generic-suite runs are not substituted for that result.

## PR #52 availability/security follow-up — 2026-10-31

Preflight: branch/head `codex/any-782-password-recovery` / `206dd7d`, remote identical;
actual PR base `codex/any-758-email-verification-password-reset` / `1a6d02d` is
already an ancestor. Preserve the existing stash and untracked Mailpit diagnosis.
The unrelated full-stack review suggestion conflicts with the explicit prohibition
on running llm-worker; retain the bounded recovery verification and state its scope.

Fix plan (before implementation):
1. Add failing behavioral regressions for retained terminal rows, active-budget
   concurrency/rollback and trusted client-source resolution.
2. Restrict capacity counts to pending/leased under the existing transaction
   advisory lock. Keep separate budgets and notification enqueue in the reset UoW.
   Reuse the existing partial active index (at most 11,000 active rows); no schema
   change is needed. Order indexed terminal cleanup, 500 rows per pass, seven-day
   retention. Admission rate ceilings bound historical creation independently of
   backlog: recovery <=1,000/hour and successful resets <=300/minute, approximately
   3.2 million terminal rows per seven days at the theoretical maximum. Cleanup
   runs before each delivery/idle iteration; 500 per pass exceeds maximum admitted
   throughput even with the 30-second SMTP deadline. Worker outages stop terminal
   creation and bound unfinished rows; restart resumes expiry cleanup. Operators
   must monitor storage/worker health and provision for this retention envelope.
3. Share an async source resolver between confirmation/recovery. Trust only peer
   IPs obtained from explicitly configured proxy service names/IP literals, with
   bounded DNS resolution; Compose configures the internal `app` service name so
   container replacement does not require stable Docker addresses. Default direct
   API configuration trusts no proxy. Ignore forwarded values from other peers;
   missing/malformed single-address data falls back to the actual peer. Never log
   resolved addresses. Uvicorn retains disabled proxy-header rewriting.
4. Nginx overwrites X-Scope-Guard-Client-IP with $remote_addr. Its optional real-IP
   configuration trusts only explicit upstream proxy CIDRs; default trusts none.
   Production path is browser -> Dokploy/Traefik -> app Nginx -> internal backend.
   Operators must configure the actual isolated Traefik network CIDRs and ensure
   the edge overwrites forwarding data. No wildcard trust or new backend exposure.
5. Verify focused PostgreSQL concurrency/capacity/rollback/retention and shared
   resolver cases; exercise actual Nginx -> backend, RU/EN Mailpit/auth journey,
   origin/cookies/confirmation, lint/types and current/minimum Compose config.
   Record fresh revision/image/mount/service evidence separately below, then commit,
   push this branch, update existing PR #52 and inspect its actual refs and new CI.

### Fresh verification for the two findings (not earlier PR evidence)

Tested source: HEAD `206dd7d0f9e6d6d95c4a965e4c4ced3a7215730d` plus this
follow-up's local changes: active-only capacity/ordered retention cleanup; shared
proxy resolver/config; Nginx header/real-IP setup; Docker/Compose/env/docs and
behavioral regressions. Migration head remains `0011_password_recovery` unchanged.

- Red reproduction: `pytest tests/integration/test_password_recovery.py -k
  capacity_cleanup` failed at admission after 10,000 retained accepted jobs.
  Resolver tests initially failed for the absent resolver. Subsequent focused
  run: 19 passed; expanded run below includes the additional concurrency test.
- Workspace Python `.venv/Scripts/python.exe`, from backend: `-m pytest tests/unit
  tests/api tests/architecture tests/integration/test_password_recovery.py
  tests/integration/test_recovery_limits.py tests/integration/test_auth_tokens.py
  tests/integration/test_email_confirmation.py tests/integration/test_release_migration.py
  tests/integration/test_schema_compatibility.py tests/integration/test_migration_lock.py
  tests/integration/test_compose_startup.py -q -p no:cacheprovider
  --basetemp=D:/Devpy/ScopeCreepGuard/output/fix52-regressions --require-integration`:
  **971 passed**, 195.94s. Owned disposable PostgreSQL only. Includes 10,000 retained
  terminal recovery jobs, 1,000 retained accepted notifications followed by real
  reset/delivery, mixed pending/leased budgets, concurrent recovery admissions and
  competing resets at notification capacity, intact losing token/password/session,
  trigger-induced enqueue rollback and bounded 500-row cleanup. Also existing
  auth/token/takeover/confirmation, source/global limits, migration/schema gates.
- `ruff check backend apps/api`, `ruff format --check backend apps/api`: pass.
  Mypy both default and `--platform win32`: pass (248 files).
  `scripts/export_openapi.py --check ../ci/contracts/openapi.json`: pass, no API
  contract change. Frontend `node scripts/api-types.mjs --check`, TypeScript,
  ESLint and dependency boundaries: pass. `node node_modules/vitest/vitest.mjs run`:
  **409 tests / 55 files passed**. No new manual browser session claimed here.
- `scripts/verify_docker_startup.py --config-only`, current Compose **5.6.0** and
  checksum-verified **2.24.0** via `--compose-binary`: pass, including production
  parity/internal proxy settings, component closures and migration gating. Config
  inspection includes llm-worker definitions but never starts/uses that process.
- Fresh builds using existing contexts/tags, `SOURCE_REVISION=
  206dd7d0f9e6d6d95c4a965e4c4ced3a7215730d-fix52-dirty`; these labels explicitly
  identify modified source, not a clean old revision. API/email-worker image:
  `sha256:85dd707a799d3b373ae8e89e0424a08a2d6c0e8460ac7f8d89b7ff57843f98f3`.
  Final frontend image:
  `sha256:d19a03aca5edfba75408516c15daedd888dc4b29a0601030bb7fe6e60a2576d6`.
  Both freshly built, **zero source mounts**. Initial frontend image `c6634185...`
  was superseded by the final stricter zero-prefix validation image; the complete
  contour was repeated after app recreation on the final image.
- `scripts/verify_react_proxy.py --image scope-guard-frontend:any782`: **23 real-image
  checks passed**, including spoofed headers discarded, explicit trusted edge
  real-IP recursion, cookies/Origin, route/error/cache behavior.
- Existing component conventions with generated synthetic settings, project
  **scg-any782-91ea6b67b5**: PostgreSQL, one-shot migrate, backend, app, email-worker,
  pinned Mailpit and existing private S3 test fixture. No llm-worker, LLM requests,
  full-stack startup, database reset, volume removal or pruning. The local wrapper
  only redirects the existing harness's output/state to a fresh owned directory.
  `verify_password_recovery.check` and `check_client_sources` passed on final
  images: RU/EN Mailpit recovery, non-consuming GET, reset, old session/password
  rejection, ordinary new-password login and notification. Actual backend and
  email-worker containers each made 11 requests through Nginx with forged changing
  headers: each independently received ten 202s then 429. A direct backend client
  likewise could not spoof its source. App recreation additionally exercised DNS
  refresh. All owned services/storage stopped afterwards; volumes retained.
- Independent code review found only the new shell script's Windows line-ending
  hazard; fixed with `.gitattributes` LF enforcement. Final lint/format checks pass.

Deployment requirement: configure `SCOPE_GUARD_EDGE_PROXY_CIDRS` for the actual
isolated operator-controlled Traefik network before public rollout; otherwise its
users safely share the edge quota. Backend DNS proxy names are an explicit trust
boundary; never share/alias the app identity with untrusted containers. Storage
must be provisioned/monitored for the documented retention envelope. Mailpit proves
local acceptance only. These results establish the password-recovery contour,
not full application-wide readiness. Existing PR remains integration-targeted;
no aggregate PR or Linear status changes are part of this follow-up.

## PR #52 CI review correction — 2026-10-31

User explicitly requests the standard full-stack smoke in addition to recovery
verification, superseding the earlier branch-specific CI exclusion. Plan: remove
ANY-782 conditions from the standard smoke and backend pytest selection; run the
recovery journey as an additional unconditional step using the same built images.
Do not run llm-worker/full stack locally. CI's existing isolated standard harness
starts the normal topology with synthetic settings and no paid/provider jobs.
Validate workflow structure and existing CI configuration tests, push the existing
branch, and inspect fresh CI without weakening any failing checks. Earlier green
recovery-only CI is historical evidence, not proof of restored full-stack checks.

Local validation at `a44c70a` plus these three-file changes: CI policy/configuration
suite `python -m unittest discover -s ci/tests -v`: **14 passed** (46.070s).
Parsed-workflow assertions confirm standard smoke precedes the additional recovery
smoke, neither has a branch condition, and backend uses unfiltered
`pytest --require-integration`. `git diff --check`: pass. Runtime suites are left
to the restored isolated CI; no local full-stack/llm-worker run was made.
