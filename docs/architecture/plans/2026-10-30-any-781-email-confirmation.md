# ANY-781: email confirmation implementation plan

Goal: register, persist pending identity and a 24-hour purpose-bound token, send
through EmailService, explicitly confirm in React, then permit workspace access.

Base: codex/any-758-email-verification-password-reset at
456838663fcba4a10ed4d8fdc32c135a2b6c2017 (ANY-779 #48 and ANY-780 #50 merged;
combined push and proposed-merge CI successful). Task branch:
codex/any-781-email-confirmation. Use the existing checkout and dependency
environments; no worktree, commit, push, PR or merge. Preserve the existing stash
and unrelated ANY-778 diagnosis report.

## Ordered implementation

- [x] Extend current internal user mapping with verification state; expose only
  workspaceAccess. Keep session-version verification. Enforce access in current
  and supported legacy product dependencies, leaving identity/logout/email flows
  reachable. Preserve legacy exemption without fabricated verification.
- [x] Add PostgreSQL send-attempt accounting and a minimal forward migration with
  schema manifest/validator updates. Atomically reserve before network I/O:
  60-second account cooldown, 5/account/hour, 30/source/hour. Count failed and
  ambiguous attempts; return Retry-After. Use direct peer address (never arbitrary
  forwarding headers), stored as domain-separated HMAC. Preserve earlier tokens.
- [x] Persist account before issuance and SMTP. Reuse AuthTokenService and
  EmailService with explicit ru/en locale. Return 201 and a valid pending session
  even when mail fails; report accepted/failed/unknown/not_attempted honestly.
  Recover interruptions through login/resend. No transaction spans SMTP; no retry.
- [x] Extend /me and add POST /api/auth/email/resend (session recipient only) and
  POST /api/auth/email/confirm ({userId,token}, no cookie required). Confirmation
  never authenticates or substitutes the signed-in user. Preserve origin checks.
  Update source schemas/OpenAPI/generated types/error catalog and RU/EN messages.
- [x] Build links from configured trusted public URL, HTTPS in production and
  local HTTP only in development. Put owner and token in URL fragment. GET never
  consumes a token. Confirmation requires an explicit button; no effect POST.
- [x] Reuse auth shell for /verify-email and /confirm-email. Restore pending state
  from /me, use focus refresh, distinguish 401/pending/backend errors, avoid
  redirect loops and mounting workspace providers before access. Restrict returnTo
  to product routes. Keep raw tokens out of storage/history state/logs/telemetry;
  no-referrer and no third-party resources; clear fragment after success.
- [x] Verify backend/HTTP/concurrency/migration and React behavior, duplicate
  registration takeover regressions, revocation and historical schema safeguards.
  Perform real browser EmailService -> aiosmtplib -> Mailpit journey on actual
  disposable PostgreSQL with documented Compose entries and private test storage.
  Check RU/EN, keyboard/status labels and mobile layout. Run lint/format/types,
  contract generation checks and diff checks. Record actual results and gaps.

## Boundaries and recovery

No password recovery UI (ANY-782), new infrastructure/outbox/worker, external
delivery, paid LLM requests, database reset, volume deletion or Docker prune.
Only SMTP acceptance is reported as accepted; timeouts/disconnects and interrupted
attempts are unknown. Successful confirmation uses the existing single-use atomic
apply/sibling revocation. Invalid tokens never become success due to a session.
Another browser offers login; a different signed-in account is never replaced.

## Evidence and handoff

Implementation and local verification completed on 2026-10-31; release-image and excluded-test gaps are recorded below.

Ruling: public URL is optional for non-email roles. Production sending without an
explicit URL fails closed; worker startup must not depend on an API-only setting.
Ruling: source-limit registration returns not_attempted with the actual cooldown;
/me reconstructs source as well as account cooldown. Direct-peer proxy/NAT clients
share the source quota; no untrusted forwarded-header policy was introduced.
Ruling: existing Draft-collection and revocation tests explicitly confirm their
new users through AuthTokenService before exercising product operations.

Verification recorded so far:

- Frontend: 54 files / 406 tests passed. Existing tsc, ESLint, module boundaries,
  generated API type check and Vite production build passed. Existing bundle-size
  warning remains (about 693 kB minified JS).
- Backend: 92 API tests passed; all three new PostgreSQL confirmation tests passed,
  including concurrent source/account limits and SMTP ambiguity recovery.
  Existing Draft collection passed after fixture confirmation was added.
- Ruff lint/format and diff checks passed. Mypy passed for 242 source files on
  default and win32 platforms. OpenAPI export check passed.
- The initial full run started while Docker was unavailable and is invalid as a
  readiness result. Subsequent broad runs were interrupted before a summary.
  One exposed an obsolete auth-route list and an unconfirmed Draft fixture; both
  have passing focused reruns. Two existing tests build extra Docker images
  (entrypoint signals and S3 restart), so the final broad run excludes those files
  to respect the resource boundary. Its result belongs in backend-scoped.xml.
- Actual browser: EN pending registration recovered through resend after detecting
  an old API image lacked aiosmtplib. Fresh scoped API build fixed that prerequisite.
  Resend accepted through EmailService -> aiosmtplib 5.1.3 -> Mailpit; pending refresh
  retained identity. Opening GET left email_verified_at NULL and used token count
  zero. Explicit keyboard button POST confirmed, cleared fragment and opened
  workspace; the original tab's refresh also opened workspace.
- Actual RU mobile (390 x 844): registration sent the RU template immediately;
  pending status/cooldown/layout were checked. After logout, explicit confirmation
  succeeded and offered sign-in without authenticating the browser.
- API and proxy logs were checked against the captured raw tokens: no matches.
  Document policy is no-referrer, scripts are local. Global analytics rendering
  was removed to avoid a previously loaded tracker persisting into the token page.

Evidence lives under ignored output/any781/: frontend-tests.log, api-final.log,
email-final.log, draft-collection-final.log, mypy*.log, backend-scoped.*,
verification.json and screenshots. No raw email tokens are stored in that JSON.

Tested base revision: 456838663fcba4a10ed4d8fdc32c135a2b6c2017 plus uncommitted
ANY-781 source. Fresh scope-guard-api:any781 image ID:
sha256:4493df5b64145fe75176f18938d98c315a25fa03e699f4cccdf4791a9b05d2e0,
revision label matching the base (local modifications are explicitly additional).
The full local stack ran in scg-any781-8f1699bea9 with migration gate, PostgreSQL,
API, app, both workers, pinned Mailpit and private Silo bucket. It reused cached
frontend/worker images with read-only current source/current dist mounts; this is
local journey evidence, not pristine release-image acceptance. Existing volumes
and databases were retained. Interrupted broad tests also created an entrypoint
fixture image; it was preserved, not pruned. No paid LLM or external SMTP calls.

Remaining limits: no external inbox-delivery claim; no fresh frontend/worker image
acceptance; entrypoint/S3 image-building tests excluded from final broad run. Full E2E
requires migration gate, PostgreSQL, API, app, both workers, Mailpit and private
test object storage; bounded checks are not full application readiness.
ANY-781 owns confirmation/access; ANY-782 owns password recovery.


### Final results (2026-10-31)

`python -m pytest -q -p no:cacheprovider --tb=short
--ignore=tests/integration/test_entrypoint_signals.py
--ignore=tests/integration/test_s3_exports.py
--basetemp=../output/any781/pytest-scoped
--junitxml=../output/any781/backend-scoped.xml` (from backend):
1050 passed, 3 failed, 641.09 seconds. These failures were obsolete confirmed-user
preconditions in metrics/profile tests and the frozen HTTP user envelope lacking
workspaceAccess. Runtime access enforcement was retained; the tests now confirm
users with AuthTokenService and explicitly adapt the additive field without
editing frozen fixtures.

Final rerun: `python -m pytest tests/unit/test_http_contracts.py
 tests/integration/test_marketing_metrics.py::test_t2_failure_keeps_authenticated_api_result_and_rollback_is_atomic
 tests/integration/test_profile_activity_runtime.py::test_authenticated_profile_api_and_browser_sessions
 -q -p no:cacheprovider --tb=short` - 22 passed in 21.48 seconds.
All three failures passed this rerun; no single all-green broad run is claimed.
The excluded files contain two entrypoint signal cases and one S3 image/restart
case. CI/release acceptance owns these remaining image-building checks.

All auth/generation/drafts gateway harnesses passed (15 auth / 14 project checks
per harness; generation uses controlled fixtures, with no paid calls).
Frontend final focus regression: 9 screen tests passed, in addition to the
54-file/406-test full run; this adds one test after that run. Frontend type/lint
checks remained green. Ruff covers 410 Python files; both mypy targets cover 242
source files. At verification time the local source tree was uncommitted; no push or PR had been created.

The dedicated Compose project and standalone test Silo are stopped after
verification; volumes, databases, images, prior stash and unrelated report remain.

Publication authorized separately by the user on 2026-10-31: commit and push ANY-781,
then open a PR targeting the integration branch. No merge is authorized.


### CI smoke follow-up (2026-10-31)

The original PR run 41139271541 passed backend, frontend, rebase and minimum
Compose checks. Its container smoke failed because it stopped Mailpit before
registration and expected onboarding access for a pending account.

The smoke now selects an available loopback frontend port before startup and
configures the trusted public URL/allowed origin consistently. Production config
fixtures use their own HTTPS origin. Registration asserts pending access and 403;
test-only Mailpit API capture is polled every 0.2 seconds with a 15-second deadline
and bounded HTTP timeouts. The captured link must have the expected origin, owner
and fragment token. GET does not consume it. A separate cookie-free client posts
confirmation and stays anonymous; the original session refreshes to allowed and
replay fails. Only then is Mailpit stopped, before existing onboarding/project/
draft checks. No fixed delivery sleep or automatic SMTP resend was added.

Regression evidence: 5 new polling/security tests first failed before the helper
existed, then passed. Combined polling/startup/fixture-isolation checks: 17 passed
in 5.86 seconds. Ruff lint/format, diff checks and config-only Compose 5.6.0 passed.
Using the previously owned scg-any781-8f1699bea9 stack with cached images verified
registration 201, pending 403, captured mail, non-consuming GET, public confirmation
200, anonymous /me 401, original-session access, replay 400 and onboarding/project/
draft access with Mailpit stopped. No images were built for this fix. Test data
and volumes remain; the stack and private Silo were stopped afterward.

This is focused local verification. The complete smoke lifecycle is left to the
fresh CI run after this correction is pushed. Evidence: ignored
output/any781/smoke-confirmation-fix.json and smoke-config-fix.log.
