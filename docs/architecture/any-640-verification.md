# ANY-640 — slices A and B verification and handoff

Date: 2026-10-10. Branch: `codex/any-640-fastapi-business-workflows`.
Exact fetched ANY-639 base and pre-publication HEAD:
`97518baacaba56a1a2542fe145b14d62644c5fda`. The slice evidence below was recorded
before publication; the final staged checks are recorded at the end.
The approved plan is [the migration plan](plans/2026-10-10-any-640-fastapi-business-workflows.md).

## Scope and ownership

Current checkpoint: Slice B. FastAPI owns the four authentication operations:
register, login, logout and me. Next.js remains the same-origin gateway and
frontend; the remaining 17 operations remain TypeScript-owned. Public-page
redirects confirm Python owner lookup. The TypeScript owner lookup remains for
still-TypeScript workflows, alongside the session verifier and signed-proof key
access. Auth endpoint hashing, credential parsing and session issuance have been
retired only after the unchanged frozen corpus passed through real forwarding.
Drizzle migration ownership and all migration files remain unchanged.

The following Slice A evidence is historical; the Slice B section records the
current checks and ownership changes.

Slice A provides common error mapping, raw object parsing, public body shapes,
response envelopes, a shared TypeScript-derived characterization corpus, Origin
protection, frontend client/forwarding foundations, and reproducible API types.
FastAPI still exposes only foundation health routes. All 21 business operations
remain owned by their existing TypeScript handlers; no frontend caller has changed
business owner and no superseded implementation has been removed.

The corpus runs actual handlers, Drizzle, bcrypt, session/proof issuance, draft
proof validation, persistence and cascading deletes in disposable PostgreSQL.
Current-user/locale resolution, rate-limit admission and LLM adapters are synthetic;
UUIDs and signed tokens are symbolic in the frozen output. It checks one successful
case per operation, unauthenticated protected operations, null bodies, duplicate
email, invalid credentials and selected field-validation precedence. Detailed
tenant, idempotency, proof-tampering, language and concurrency matrices remain
mandatory at the individual route-migration gates. Handler characterization is
not production HTTP or browser E2E evidence.

Raw body shapes are deliberately not FastAPI body dependencies: authorization,
proof-before-document checks, and route-specific error precedence must run in
the approved order when routes move. Opaque proof/document payloads stay raw until
the appropriate workflow validates them. API response models remain independent
of SQLAlchemy models.

## Observed checks

Commands below use repository root unless a working directory is specified.
All test database mutation occurred in owned, volume-free disposable PostgreSQL
containers. Application integration variables were cleared for verification.

| Command | Observed result |
|---|---|
| `node scripts/verify-any640.mjs --suite frontend` | Follow-up exit 0; 44 files, 391 frontend tests passed, including real persistence and characterization; then 19 Python contract tests passed |
| `node scripts/verify-any640.mjs --suite contracts` | Exit 0; real-handler corpus matched unchanged with `NextRequest`; 1 frontend characterization test and 19 Python contract tests passed |
| Backend: `uv run --no-sync pytest --require-integration -q --basetemp=.pytest_cache/any640-ci-followup` | Follow-up exit 0; 136 unit/API/PostgreSQL integration tests passed |
| Backend: `uv run --no-sync ruff check .` | Follow-up exit 0, all checks passed |
| Backend: `uv run --no-sync ruff format --check .` | Follow-up exit 0; all 66 files formatted |
| Backend: `uv run --no-sync mypy src/scope_guard` | Exit 0; no issues in 25 source files |
| Backend: `uv run --no-sync python scripts/export_openapi.py --check ../contracts/openapi.json` | Exit 0; generated contract fresh; business paths remain absent |
| Frontend: `corepack pnpm exec tsc --noEmit` | Exit 0 |
| Frontend: `corepack pnpm exec next typegen` | Follow-up exit 0; route types generated |
| Frontend: `corepack pnpm build`, followed by `corepack pnpm exec tsc --noEmit` | Follow-up exit 0; production build and independent post-build typing passed with synthetic configuration |
| Frontend: `node --test scripts/docker-entrypoint.test.mjs` | Follow-up exit 0; 3 passed, 0 skipped |
| Frontend: `corepack pnpm test lib/api/forward.test.ts lib/api/origin.test.ts` | Follow-up exit 0; 16 passed |
| Frontend: `corepack pnpm lint` | Exit 0; two inherited unused-variable warnings in LLM tests |
| Frontend: `corepack pnpm api:types:check` | Exit 0; committed types reproduce from OpenAPI |
| `docker compose -f compose.yaml --profile app config --quiet` | Exit 0; no services started |
| `docker compose -f docker-compose.yml --profile app config --quiet` | Follow-up exit 0; legacy entry point valid, no services started |
| `docker compose -f docker-compose.dokploy.yml config --quiet` | Exit 0 with synthetic process configuration; no services started |
| `docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet` | Follow-up exit 0; production entry point valid, no services started |
| `node scripts/verify-any640.mjs --suite containers` | Exit 0; both final production images built; eight production HTTP checks passed; owned containers removed |
| `git diff --check` | Exit 0; only Git line-ending notices |

## Slice A follow-up — CI and current handoff

The ignored root handoff now points to the ANY-640 plan in both its checkpoint
and planning sections. Its backend ownership description includes inherited
ANY-639 models/lifecycle/baseline while retaining TypeScript business ownership.
No branch switch, commit, push or business cutover occurred.

`.github/workflows/checks.yml` now triggers for PRs into `main`, the current
ANY-639 parent, and the retained ANY-638 parent. Push checks include `main`,
ANY-639 and the current ANY-640 child. The separate rebase workflow remains
main-only, so stacked PRs do not need an incorrect rebase onto main.
Backend CI runs mandatory integration tests, Ruff lint/format, mypy and OpenAPI
freshness. Frontend CI installs the locked Python verification dependencies and
uses the owned test harness, replacing its fixed PostgreSQL service target.
That command runs the full frontend suite and frozen corpus without silently
skipping the compatibility test. It also retains entrypoint tests, lint, route
type generation, explicit TypeScript checks before/after build, production build,
and adds `pnpm api:types:check`. Build configuration uses a synthetic unreachable
database target, and ordinary checks cannot call real OpenAI.

Workflow validation command (PowerShell, repository mounted read-only):

```text
docker run --rm -v 'D:/Devpy/ScopeCreepGuard:/repo:ro' -w /repo rhysd/actionlint:latest
```

Observed: exit 0 after correcting the existing container liveness loop's unused
counter reported by ShellCheck. Validator image digest:
`sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667`.
The workflow was validated locally and its commands exercised; remote GitHub
Actions execution has not occurred because no commit/push was authorized.

New real-loopback transport checks confirm the configured backend receives its
own Host header even with caller routing headers, export content/disposition,
retry/correlation headers and Unicode bytes survive, and a disconnected backend
receives exactly one request before the helper returns 503. Existing checks
preserve individual cookies, status and raw body/query, reject caller-selected
upstream targets, and do not follow redirects. No existing business handler
imports this helper; it remains prepared infrastructure, without retries or
TypeScript fallback. FastAPI remains separately containerized; eight production
HTTP smoke checks passed again without attaching a database. Cross-origin write
protection still runs before `/api/*` handling and adds no CORS policy.

Follow-up failures recorded: Ruff initially found one verification-script line
needing reformatting; corrected and all 66 files then passed. One full frontend
run under concurrent build/backend load timed out in the first forwarding case
at its five-second limit (390 passed, one failed). That case included deferred
module loading; the constant import now runs before test timing. No production
deadline or assertion was relaxed. The subsequent full suite passed 391/391.
Inherited Vite/middleware deprecation and two lint warnings remain.

No changes exist under `frontend/app/api`, `frontend/drizzle` or `backend/alembic`
relative to the parent. No application migration, CORS addition, microservice,
staging, commit, push or Slice B work occurred. Disposable test fixture setup is
the only database mutation used for verification.

Container verification command: `node scripts/verify-any640.mjs --suite containers`.
It builds both production images (frontend build includes `pnpm build`), then
checks eight HTTP outcomes: Python liveness and foreign-Origin rejection; frontend
foreign-Origin rejection on three public/protected write paths; successful locale
write and browser-readable cookie; allowed-origin unauthenticated analysis; and
originless locale write. No database is attached. Container cleanup checks the
immutable container identifier and ownership label. This verifies production
middleware and HTTP boundaries, not authenticated browser workflows. The build
disables its inherited TypeScript build check, so separate `tsc` evidence above
is required. Browser E2E and cross-runtime session/proof interchange remain gates
for B/D/E/G, not claims made for slice A.

## TDD and review record

- Errors/Origin: observed 24 failing tests and one baseline pass before implementation;
  then 25 passed. A server-boundary regression subsequently reproduced raw exception
  propagation; after middleware correction, all 26 passed without propagating raw
  exceptions to server traceback logging.
- Forwarding: six missing-module failures before implementation, then six passed.
  Origin: seven failures and one baseline pass, then eight passed. Client: missing
  module before implementation, then five passed. Combined transport/client/Origin:
  19 passed. Real loopback forwarding checks raw payload, query, individual cookies
  including Expires commas, status/headers, manual redirects and no retries.
- Python contracts: nine failures and one pass before response/schema reconciliation,
  then ten passed. Public request models added a missing-module failure, then eleven
  passed. Independent review reproduced price-alias acceptance and date coercion;
  regression tests failed four cases before fixes, then all 19 contract tests passed.
- Full backend first run: 124 passed, two Windows temporary-directory permission
  errors. Using a dedicated workspace temp directory resolved the infrastructure
  problem; later final run passed all 136 tests.
- Fresh-context review identified two important public-input defects. Both were
  fixed and verified; no critical transport/Origin/deployment defect was established.

## Rulings and limitations

- Ruling: inventory is **21 operations across 16 route files**, not the ticket/initial
  plan's 22. Source and executable inventory agree. Corrected the plan rather than
  inventing an endpoint. Cost if wrong: a missing route would fail future inventory
  reconciliation; the current executable corpus covers every current method.
- Ruling: existing route-specific normalization/validation belongs to later route
  parsers; this slice's models describe transport shapes and preserve raw workflow
  envelopes. Using them as automatic FastAPI dependencies would violate precedence.
- Ruling: OpenAPI and generated frontend types describe implemented routes only;
  prepared business contracts do not advertise routes that do not exist.
- Ruling: explicit label fields replace dynamic `create_model` with equivalent
  fields to permit the newly approved static checker. Minimal parent type fixes
  clarify nullable money/target checks and SQLAlchemy result types; no migration
  ownership, schema or application-database mutation changed.
- Ruling: use Undici major 7 to preserve the existing Node minimum. Incoming
  cancellation controls upstream forwarding; no shorter headers/body deadline,
  retry, redirect-following, TypeScript fallback, duplicate generation or dual write.
- Ruling: per-slice human review takes precedence over skill defaults for continuous
  execution and automatic commits. Stop after A; B requires review.
- Supplied write Origins fail closed unless explicitly configured. Local examples
  and Compose include browser origins; production must supply its HTTPS allowlist.
- Known inherited warnings: middleware convention deprecated (rename in B), Vite
  native config-loader warning, two lint warnings. No ordinary verification calls
  real OpenAI. LLM retry semantics and browser journeys remain later-slice gates.
- Preserve unrelated `.gitignore`, `dev.sh`, `docker-compose.override.yml`,
  `pnpm-workspace.yaml`, `test_openai.mjs`. No staging, commits, pushes, application
  migrations, resets, clean, stash, rebase or PR-base changes were performed.
- The child currently tracks the parent remote branch after branch creation;
  any future reviewed push must name the child destination explicitly.

Historical next step after Slice A review was B. The user subsequently approved
and requested B; the current next step is C only after review.

## Slice B — authentication cutover, 2026-10-10

Branch/base/HEAD remain as recorded above. Fresh fetch confirmed the remote parent
at the exact same commit. No commit, push, rebase or application migration occurred.

Python auth workflows use repository ports and the inherited SQLAlchemy Unit of
Work. BCrypt runs outside database transactions. Registration prechecks normalized
email, then relies on `users_email_unique` for the forced concurrent race; the loser
rolls back and returns 409. Cookies are issued only after commit. `/me` reads the
stored owner, rather than trusting the token email, and expires invalid/deleted-owner
cookies. Logout is public and expires the cookie without database or secret access.

Session compatibility is proved in both directions with JOSE and bcryptjs, including
byte-identical tokens at a fixed clock, cost-12 Python hashes, legacy 2a/2b/2y hashes,
UTF-16 password length, Unicode/null/lone-surrogate encoding and 72-byte truncation.
The original cookie name, raw shared secret, seven-day lifetime, HttpOnly, Path=/,
SameSite=Lax, production Secure and serialized expiry behavior remain intact.
Python validates the actual issued format (HS256, integer iat/exp, subject/email);
signed tokens missing those issued claims fail safely. Future iat remains accepted
like JOSE. Malformed, tampered, expired and deleted-user sessions return 401.

Each of the four Next.js handlers makes one fixed-origin forwarding call. No retry,
TypeScript fallback or dual write exists. The Next 16 `proxy.ts` guard keeps pending
business APIs protected; `/login` and `/register` only redirect after Python confirms
the owner. A 401 forwards the expired cookie; backend failure permits login recovery
without clearing a valid cookie. A navigation lookup has a three-second cancellation
deadline; ordinary workflow forwarding retains incoming cancellation only.

| Command | Observed result |
|---|---|
| Backend: `uv run --no-sync pytest --require-integration --basetemp .pytest_cache/any640_b -q` | Exit 0; 166 tests passed in 62.12s, including owned PostgreSQL and cross-runtime Node checks |
| `node scripts/verify-any640.mjs --suite frontend` | Exit 0; 395 tests across 45 files passed, then 19 Python contract tests passed |
| `node scripts/verify-any640.mjs --suite contracts` | Exit 0; original 21-operation corpus unchanged with real Python auth HTTP and TS remaining workflows; then 19 contract tests passed |
| Frontend: `node node_modules/vitest/vitest.mjs run tests/auth-boundary.test.ts tests/auth-gateway.test.ts lib/api/origin.test.ts` | Exit 0; 21 tests passed |
| Backend: `uv run --no-sync ruff check .`; `uv run --no-sync ruff format --check .`; `uv run --no-sync mypy src/scope_guard` | All exit 0; 79 files formatted, 32 source files typed |
| Backend: `uv run --no-sync python scripts/export_openapi.py --output ../contracts/openapi.json`, then `--check ../contracts/openapi.json` | Exit 0; six implemented paths, four auth operations and their request bodies documented |
| Frontend: `node scripts/api-types.mjs`; `corepack pnpm api:types:check` | Exit 0; generated auth types fresh |
| Frontend: `node node_modules/next/dist/bin/next typegen`; `node node_modules/typescript/bin/tsc --noEmit`; `node node_modules/next/dist/bin/next build`; post-build `node node_modules/typescript/bin/tsc --noEmit` | All exit 0; production build with synthetic unreachable DB, explicit type checks passed |
| Frontend: `node node_modules/eslint/bin/eslint.js .`; `node --test scripts/docker-entrypoint.test.mjs` | Exit 0; two inherited lint warnings; 3 entrypoint tests passed |
| `node scripts/verify-any640.mjs --suite auth-gateway` | Exit 0; 15 checks through production Next.js, FastAPI and owned PostgreSQL, including deleted-owner page recovery and Python session accepted by TS projects; rerun passed after review clock fix |
| `node scripts/verify-any640.mjs --suite containers` | Exit 0; both production images built; 8 HTTP deployment smoke checks passed; owned containers removed |
| `docker compose -f compose.yaml --profile app config --quiet`; `docker compose -f docker-compose.yml --profile app config --quiet`; `docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet` | All exit 0; no application services or databases modified |
| `docker run --rm -v 'D:/Devpy/ScopeCreepGuard:/repo:ro' -w /repo rhysd/actionlint:latest`; `git diff --check` | Both exit 0; CI workflow valid; only Git line-ending notices |

TDD evidence: adapter checks first failed for absent modules; API checks first saw
404; gateway regression failed on forbidden TypeScript DB import; page recovery
checks failed on the old redirect. Each passed after implementation. Initial full
backend run found the obsolete health-only OpenAPI inventory; it was corrected,
then all 166 tests passed. Windows HTTP harness uses the inherited explicit
Psycopg-compatible loop factory. Independent review found the gateway test must use
real time while corpus replay uses frozen time; fixed and rerun successfully.

CI retains main and stacked-parent PR targets, mandatory backend checks, frontend
tests/types/build/generated freshness, and now the production auth gateway journey.
Local/native auth requires shared AUTH_SECRET and backend origin configuration.
Production Compose passes that same secret to both services and enables Secure
cookies; native development defaults to non-Secure. Do not supply a different
SCOPE_GUARD_AUTH_SECRET than the frontend AUTH_SECRET during this transition.

Limits: the gateway journey is production-server HTTP integration, not a browser
form-click test. Complete Playwright product journeys remain Slice G's gate.
Remote CI has not run; changes remain local. Vite loader and two inherited lint
warnings remain; Next's deprecated middleware file has been replaced with proxy.
No business generation, proof, language, snapshot or migration behavior was moved.

Next: review Slice B. Slice C (projects/history/ownership) is not started.

## Final staged verification before publication — 2026-10-10

The user explicitly authorized committing completed slices A/B and pushing only
`codex/any-640-fastapi-business-workflows`, without PR changes. Branch and HEAD
were checked against the exact parent above. The index contains 69 ANY-640 files;
unrelated `.gitignore`, `dev.sh`, `docker-compose.override.yml`, root
`pnpm-workspace.yaml` and `test_openai.mjs` are excluded. The ignored root
`AGENT.md`, certificates, output folders and Drizzle migrations are excluded.
No implementation changes were made during publication preparation.

| Final command | Observed result |
|---|---|
| Backend: `uv run --no-sync pytest --require-integration --basetemp .pytest_cache/any640_publish -q` | Exit 0; 166 passed in 79.84s |
| Backend: `uv run --no-sync ruff check .`; `uv run --no-sync ruff format --check .`; `uv run --no-sync mypy src/scope_guard`; `uv run --no-sync python scripts/export_openapi.py --check ../contracts/openapi.json` | All exit 0; 79 files formatted, 32 sources typed, OpenAPI fresh |
| `node scripts/verify-any640.mjs --suite frontend` | Exit 0; 395 passed across 45 files in 30.36s; then 19 Python contract checks passed |
| Frontend: `corepack pnpm api:types:check`; `corepack pnpm exec next typegen`; `corepack pnpm exec tsc --noEmit`; `corepack pnpm build`; post-build `corepack pnpm exec tsc --noEmit` | All exit 0; synthetic unreachable build database; generated types and explicit typing passed |
| Frontend: `node --test scripts/docker-entrypoint.test.mjs`; `corepack pnpm lint` | Both exit 0; 3 entrypoint tests passed; two inherited unused-variable warnings |
| `node scripts/verify-any640.mjs --suite auth-gateway` | Exit 0; 15 production-server auth journey checks passed |
| `node scripts/verify-any640.mjs --suite containers` | Exit 0; both production images built; 8 smoke checks passed; owned containers removed |
| `docker compose -f compose.yaml --profile app config --quiet`; `docker compose -f docker-compose.yml --profile app config --quiet`; `docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet` | All exit 0 |
| `docker run --rm -v 'D:/Devpy/ScopeCreepGuard:/repo:ro' -w /repo rhysd/actionlint:latest` | Exit 0; CI workflow valid |
| `git diff --cached --check` and staged-path audit | Exit 0; only ANY-640 paths in index, no migration files |

All database mutations were confined to owned disposable test databases. No rebase,
branch switch, reset, clean, stash, application migration or PR change occurred.
Slice C and full browser form journeys remain outside this publication.
