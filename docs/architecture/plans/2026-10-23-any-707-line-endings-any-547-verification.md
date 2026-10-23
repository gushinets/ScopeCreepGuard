# ANY-707 Windows line endings and ANY-547 persistence verification

**Final status, 2026-10-23 18:37 Moscow: PASS for both requested scenarios.**
The earlier blocked attempts below are historical evidence, superseded by the
final verification section. No application functionality was changed.

Base: `890ec1d030b245285c0e96de2befb7cd702bfbaf`.
Branch: `codex/any-702-703-documentation-alignment`.
Workflow: user authorized this checkout; preserve the pre-existing untracked
`.taste-skill/` directory. Do not push, create a PR, or change Linear statuses.

## Scope and ordered plan

- [x] Replace the obsolete generated API path in `.gitattributes`, add the nginx
  startup script LF rule, and normalize only those two tracked files.
- [x] Run the unchanged strict `pnpm api:types:check` through Docker against the
  actual checkout, then verify normal nginx startup without file substitutions.
- [x] Exercise a fresh Windows checkout with `core.autocrlf=true` and verify LF
  bytes for both paths.
- [x] For ANY-547, edit clientEmail and endDate, save, sign out, then sign in in
  an independent browser context and reopen the project. Verify backend-loaded
  values. Change application functionality only for a reproducible defect.
- [x] Record evidence, limitations, and final Git scope here.

Exclusions: API contract edits, unrelated generation/normalization, paid AI calls,
and ANY-547 implementation changes without a reproduced defect.

## Verification evidence

Initial inspection: generated API file is `i/lf w/crlf`; nginx script is
`i/lf w/lf`; both lack an applicable LF attribute. Git core.autocrlf is true.
The freshness checker compares exact strings and remains unchanged.

After normalization, `git ls-files --eol` reports `i/lf w/lf attr/text eol=lf`
for both target paths. Raw Git object hashes match HEAD exactly:

| Path | Working bytes and HEAD blob |
| --- | --- |
| `frontend/src/shared/api/generated.ts` | `ae9393a4f5769758345281ebf4b52352921031eb` |
| `frontend/nginx/05-validate-upstream.sh` | `814ab7fd72bd4cd94cf233632f4f718c6c0ed84f` |

Fresh Windows checkout proof: initialized an isolated disposable Git repository
at ignored `output/any707-fresh-windows/`, added only the updated attributes and
two target files, deleted both working files, and ran
`git -c core.autocrlf=true checkout-index --all --force` in that repository.
Both recreated files have zero CR bytes and `i/lf w/lf attr/text eol=lf`.
The generated file has 6,810 LF bytes; the shell script has 10. This verifies
Windows checkout conversion for the exact proposed rules and target bytes;
it is not a full repository clone or CI run. The main checkout index was not
staged. An earlier alternate-index attempt could not write main-repository
objects under sandbox permissions; the isolated repository avoided that need.

Docker attempt against the actual checkout:

```text
docker run --rm --mount type=bind,source=D:\Devpy\ScopeCreepGuard,target=/checkout,readonly \
  -w /checkout/frontend scg-onboarding-frontend-check pnpm api:types:check
```

This first attempt exited 1 because the mounted Windows node_modules did not
resolve `openapi-typescript` in Linux. A Linux-only named dependency volume
(`scg-any707-node-modules`) was then prepared from the existing frontend check
image, with a retry mounting it at `/checkout/frontend/node_modules` while
keeping checkout source read-only. Docker container creation returned HTTP 502,
and subsequent Docker commands hung. No successful freshness-check result was
obtained, and no failure was suppressed. The checker and API contract are
unchanged. The dependency-volume retry has no confirmed completion result.
A final bounded `docker version` probe timed out after 20 seconds; Windows
reported `com.docker.service` as stopped. Existing Docker services were not
restarted, since that could interrupt other local work.

Normal nginx startup remains unverified: Docker initially listed the existing
`scg-local` stack as healthy, but that predates this verification. Its app uses
bind mounts for assets and the tracked startup script, so it cannot substitute
for the requested normal image-startup check. No temporary startup script or
other application file was substituted by this work. Later, an HTTP request to
`http://localhost:3000/health/live` failed with connection refused.

ANY-547 remains unverified in this session. The host browser CLI initially
failed with a memory-allocation error; retrying outside the restricted process
successfully displayed its help. The in-app browser tool failed with
`Transport closed`. The application was then unreachable, preventing the edit,
save, explicit sign-out, independent-context sign-in and backend reload scenario.
Prior backend evidence from the user is not represented as a new browser pass.
No ANY-547 functionality was changed, and no AI operation was requested.

`git diff --check` passed. Tracked content diff is limited to `.gitattributes`;
this plan is new. Normalization restored the generated file's existing HEAD
bytes, and the shell script already had those LF bytes. `.taste-skill/` remains
untouched. No push, PR creation or Linear status update occurred.

## Limitations and ownership

Follow-up owner: next executor in this chat after Docker becomes responsive.
Repeat the strict checkout-mounted freshness check with Linux dependencies,
build the normal frontend runner from this checkout and start nginx without
overrides, then run the entire ANY-547 browser scenario in independent contexts
and inspect backend response values for both edited fields. Do not infer a pass
from the line-ending proof or earlier backend verification.

## Follow-up verification on 2026-10-23

Re-inspected the existing changes and preserved them. The requested attribute
rules were already present; no additional application or contract edits were
needed. Both target working files contain zero CR bytes and report
`i/lf w/lf attr/text eol=lf`. Repeated the isolated Windows conversion checkout
with `core.autocrlf=true`; both targets again report LF working bytes.
`git diff --check` passed.

Docker access in the sandbox returned permission denied. An elevated
`docker version` probe produced no response. Attempting to start the stopped
Docker Desktop service failed: Windows could not open the service. Docker
Desktop processes exist, but this does not establish engine availability.
The application health request to localhost:3000 was refused.
Consequently the strict checkout-mounted API check, normal nginx startup,
and complete independent-context browser persistence scenario remain blocked
and are not claimed as passing. No freshness suppression, temporary file
substitution, functionality change, push, PR, or Linear update was made.
Follow-up requires restoring Docker engine access, then executing the remaining
unchecked steps above.

## Verification retry — 2026-10-23 (Docker briefly available)

Tested branch `codex/any-702-703-documentation-alignment`, commit
`890ec1d030b245285c0e96de2befb7cd702bfbaf`. Existing uncommitted scope:
`.gitattributes`, line-ending-only generated.ts status, this untracked record,
and unrelated untracked `.taste-skill/`. No application files were edited or
normalized and no branch switch occurred.

Commands and outcomes:

- PASS: `git ls-files --eol -- frontend/src/shared/api/generated.ts frontend/nginx/05-validate-upstream.sh` (0): both i/lf w/lf.
- PASS: `git check-attr text eol -- frontend/src/shared/api/generated.ts frontend/nginx/05-validate-upstream.sh` (0): text set, eol lf for both. Raw byte inspection: zero CR bytes each.
- PASS (isolated target-file checkout, not full clone): `git -C output/any707-fresh-windows -c core.autocrlf=true checkout-index --all --force` (0), followed by `git -C output/any707-fresh-windows ls-files --eol` (0): both target files w/lf.
- `docker version`: sandbox exit 1 (pipe permission denied); elevated exit 0, Docker Desktop 4.95.0 / Engine 29.8.2.
- `docker build --target dependencies -t scg-any707-dependencies frontend` (0).
- BLOCKED: `docker run --rm --mount type=bind,source=D:\Devpy\ScopeCreepGuard,target=/checkout,readonly --mount type=volume,target=/checkout/frontend/node_modules -w /checkout/frontend scg-any707-dependencies sh -c 'cp -a /app/node_modules/. /checkout/frontend/node_modules/ && pnpm api:types:check'`. First attempt exit 1: `error waiting for container: unexpected EOF`. Retry reached unchanged `node scripts/api-types.mjs --check`, then host reported `Out of memory` and Docker returned the same unexpected EOF. No reliable checker completion exit code; not a pass. Dependencies were copied from Linux image into an anonymous container volume, never Windows node_modules.
- PASS build: `docker build --target runner -t scg-any707-verified frontend`: first attempt exit 1, `rpc error: code = Unavailable desc = error reading from server: EOF`; retry exit 0. Image manifest sha256:4060caef31c4b2c104c70d87c2c169b5a6b53f2a56d310a67b63faef1eb5325c. Build emitted a nonfatal large-chunk warning.
- BLOCKED stack: `docker compose -p scg-local -f compose.yaml up -d postgres backend` (1): backend build lost Docker connection with `rpc error: code = Unavailable desc = error reading from server: EOF`.
- `docker run -d --name scg-any707-nginx-verification --network scg-local_default -p 3107:3000 scg-any707-verified` created container 7245f9ce73c8; command completion was not captured. `docker logs scg-any707-nginx-verification` and `docker inspect scg-any707-nginx-verification --format '{{json .State}}'` (0) show the normal entrypoint successfully launched 05-validate-upstream.sh and completed template substitution without CRLF errors. nginx then exited 1: `host not found in upstream "backend" in /etc/nginx/conf.d/default.conf:14`. No script or entrypoint substitution was used. Container is stopped and retained for evidence.
- BLOCKED nginx health: HTTP request to http://localhost:3107/health/live refused connection. Startup cannot pass without the backend; no product defect established.
- BLOCKED ANY-547: real backend stack could not start, so no synthetic account, browser edit/save/sign-out/independent-context login/reload scenario was performed. No screenshots or API evidence exist for this retry; prior API results are not a browser pass. No user data was modified.
- PASS: `git diff --check` (0).

Docker was not reset and no volumes were deleted. No paid calls, commit, push,
PR, or Linear changes. Remaining owner: next executor after Docker resource /
connection stability is restored; rerun strict checker, complete normal-stack
nginx health verification, and execute the full browser scenario.

## Sequential retry — 2026-10-23 17:48 Moscow

User confirmed Docker is running. Rechecked without resetting Docker:
`docker ps --format '{{.Names}} {{.Status}} {{.Ports}}'` and
`docker images --format '{{.Repository}}:{{.Tag}}'` both completed (0).
Only scg-local-llm-worker-1 was running. Existing Git state was unchanged.
Retried the exact checkout-mounted Linux-dependency freshness command above
alone: exit 1, `error waiting for container: unexpected EOF` at 17:48:57.
A subsequent inspection/stats shell failed with exit -2146233082:
`Fatal error. Releasing the double mapped memory failed`.
Thus Docker availability is confirmed, but command execution remains unstable;
API freshness and browser verification remain BLOCKED. No application edits,
container resets, volume deletion, or user-data changes were performed.

## Alternate shell retry — 17:49–17:51 Moscow

Used cmd.exe to avoid the earlier PowerShell memory error. `docker ps -a`
passed (0). `docker start scg-local-postgres-1 scg-local-backend-1` passed
(0); PostgreSQL became healthy, but backend subsequently exited 1.
Retried unchanged strict check using an ignored helper shell script containing
only Linux dependency copy and `pnpm api:types:check` (no product substitutions).
Command: `docker run --rm --mount type=bind,source=D:\Devpy\ScopeCreepGuard,target=/checkout,readonly --mount type=volume,target=/checkout/frontend/node_modules -w /checkout/frontend scg-any707-dependencies sh /checkout/output/any707/check.sh`.
It reached the strict checker then exited 125 with unexpected EOF.
`docker logs --since 3m scg-local-backend-1` and
`docker start scg-any707-nginx-verification` then both exited 1 with explicit:
`Docker Desktop is unable to start`, `DockerDesktop/Wsl/ExecError`,
WSL bootstrap exit status `0xc00000fd`. This establishes an engine bootstrap
failure beyond the earlier ambiguous EOF. No Docker reset was performed.
Both remaining scenarios remain BLOCKED; no browser or backend values claimed.

## Retry at 18:02–18:04 Moscow

Docker ps/version passed (0), confirming the engine responds. Started existing
PostgreSQL and backend containers (0). Backend logs revealed
`schema_mismatch: unknown_alembic_revision`; old image cannot serve current DB.
Attempted current checkout build:
`docker compose -p scg-local -f compose.yaml build backend` (1), after dependency
download stalled: `failed to receive status: rpc error: code = Unavailable desc = error reading from server: EOF`.
Retried checkout check command using output/any707/check.sh: exit 125,
`error waiting for container: unexpected EOF`. Docker version immediately
subsequently passed (0). Engine responsiveness does not establish sustained
build/container execution. No schema or application modifications performed.
ANY-547 and strict check remain BLOCKED, not product failures.

## Image replacement and successful clean-stack startup

Removed confirmed local app/backend containers with
`docker compose -p scg-local -f compose.yaml rm -s -f app backend` (0),
removed stopped scg-any707-nginx-verification (0), and removed
scg-any707-verified/scg-any707-dependencies image tags (0). Additional removal
of onboarding/LLM containers was rejected by automatic approval review because
ownership was not confirmed; these were preserved. No volumes deleted.

Current app/backend images successfully built. Repeated download/build attempt
initially lost Docker connection, but final build completed. Starting against
existing local PostgreSQL failed with `schema_mismatch: unknown_alembic_revision`
even with current backend image. Existing DB was not altered to repair this.

Created isolated stack with new synthetic-data volume:
`$env:FRONTEND_PORT='3107'; $env:BACKEND_PORT='8107'; $env:POSTGRES_PORT='5507'; docker compose -p scg-verification -f compose.yaml up -d --build postgres backend app`
(exit 0). Both images built; PostgreSQL and backend healthy; app started.
`docker exec scg-verification-app-1 wget -q -O - http://127.0.0.1:3000/health/live`
(exit 0), response `{"status":"ok"}`. Normal Dockerfile/entrypoint used with no
startup substitutions. ANY-707 normal image startup/health now PASS.
Verification frontend is http://localhost:3107. Existing local database and
other containers/images retained. Strict freshness and ANY-547 browser scenario
still require completion; startup alone is not represented as those passes.

## Final verification — 2026-10-23

All requested checks now PASS; earlier environment failures remain above as
history, not current limitations.

- Strict checkout freshness: exit 0 for
  `docker run --rm --mount type=bind,source=D:\Devpy\ScopeCreepGuard,target=/checkout,readonly --mount type=volume,target=/checkout/frontend/node_modules -w /checkout/frontend scg-any707-dependencies sh /checkout/output/any707/check.sh`.
  The ignored helper only copies image Linux dependencies into the isolated
  dependency volume and runs `pnpm api:types:check`. Product source and contract
  are read directly from the actual checkout, read-only. No generated content,
  freshness comparison or failure handling was changed.
- Normal nginx startup: `docker inspect scg-verification-app-1` confirms
  `Mounts=[]` and health `healthy`. Logs show the normal entrypoint launching
  `05-validate-upstream.sh` and `Configuration complete; ready for start up`.
  `docker exec scg-verification-app-1 wget -q -O - http://127.0.0.1:3000/health/live`
  exits 0 with `{"status":"ok"}`. No startup file/entrypoint substitutions.
- Repeated isolated Windows checkout conversion with core.autocrlf=true:
  deleted and checked out the two target files from the disposable repository's
  index. Both report `i/lf w/lf attr/text eol=lf`, zero CR bytes. This is a
  targeted checkout-conversion test, not a full repository clone.
- ANY-547 complete browser scenario: registered a synthetic account in the
  isolated verification database and created project
  `b314b5ae-4ff4-448c-aa20-83b9b7188ca7` with clientEmail
  `before-any547@example.test` and endDate `2026-12-15`. Opened Projects > Edit,
  changed both to `after-any547@example.test` and `2027-02-17`, clicked Save
  project, required an OK PATCH response, then explicitly clicked Logout and
  waited for the login form.
- Created a separate Playwright browser context using `browser.newContext()`
  with no storageState or shared cookies; asserted its cookies were empty.
  Set only the English locale cookie, signed in through the UI, captured the
  new session's `GET /api/v2/projects` response (HTTP 200), and asserted both
  edited values on that project. Opened Projects > Edit and asserted both form
  values equal the backend response. All assertions passed.
- Evidence: ignored `output/playwright/any547/verify-independent.js` and
  `output/playwright/any547/independent-context-reopened.png`; screenshot visually
  inspected. The independent context was closed after verification.
- Setup only: isolated `scg-verification` backend required workflow v2 enabled
  and migration target head; defaults had returned 503 (disabled workflow),
  then 500 (missing v2 schema). The ignored overlay
  `output/any707/compose.verify.yaml` enables v2, disables LLM workflow and
  migrates only the new synthetic database. No existing local DB was changed.
  The isolated nginx container was restarted during setup, with normal startup.
- Final `git diff --check` exits 0. Generated source raw blob hash still equals
  HEAD (`ae9393a4f5769758345281ebf4b52352921031eb`); target working files are LF.
  Content changes remain only `.gitattributes` and this new plan; generated.ts
  normalization changes checkout bytes only, and nginx was already LF.
  Pre-existing `.taste-skill/` remains untouched.

Remaining limitations: verified on the isolated local Docker stack and synthetic
account, not production. No ANY-547 defect was reproduced; no implementation
change was needed. No paid AI calls, pushes, PRs or Linear status changes.
The verification stack and synthetic test data are retained for inspection.
Follow-up owner: this chat; no remaining requested verification work.

## CI rebase gate follow-up — 2026-10-23

Plan: fetch current main, rebase this branch without merge commits, run the
unchanged `ci/scripts/require-rebase.sh main`, then update the existing remote
branch with an explicit force-with-lease. Preserve `.taste-skill/`.

Cause: main advanced to `9f56820` with the already-applied ANY-702/703
 documentation commit; the feature branch was no longer based on current main.
`git rebase origin/main` succeeded and correctly skipped equivalent commit
`890ec1d`. The resulting application/file tree matched pre-rebase `e8bb889`.
`D:/Git/bin/bash.exe ci/scripts/require-rebase.sh main` exited 0, and
`git diff --check` passed. The gate was not modified or suppressed. No API or
ANY-547 functionality changed. Push authorized by the user; no PR/status change.
