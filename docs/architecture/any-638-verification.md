# ANY-638 implementation handoff

## Checkout, base and scope

Implemented in `D:/Devpy/ScopeCreepGuard`, without a worktree, following the user's
superseding instruction. Dedicated branch:
`codex/any-638-frontend-backend-foundation`. Freshly fetched base:
`753c88af7f2b647e3bc52f750db4d5b5d17aa03e`. No commit, push, stash, reset or clean.

Read current Linear descriptions for ANY-638, ANY-637, ANY-639, ANY-640 and ANY-641.
All scoped implementation steps are complete: frontend relocation; FastAPI
foundation; shared local/production deployment; generated contracts, boundaries,
setup documentation and CI. Runtime verification limitations are explicit below.

Next.js retains every existing business API, auth guard/session, Drizzle schema
and all seven migrations, LLM prompts, pricing/language behavior, saved draft
snapshots/proofs, project mutations and document/evaluation helpers. Python owns
only startup, logging/settings and GET /health/live. No SQLAlchemy, Alembic,
database connections, workers, migrated business routes or document services.

## Baseline and results

Commands below were executed from the relevant application directory. pnpm is
always selected through Corepack at the manifest's pinned 10.34.1 version.

| Check | Result |
| --- | --- |
| Pre-move Vitest suite | 337 passed; 23 disposable-database tests skipped |
| Pre-move ESLint | Passed; two existing unused-variable warnings |
| Pre-move TypeScript / production build | Passed |
| `corepack pnpm install --frozen-lockfile` in frontend | Passed |
| `corepack pnpm test` in frontend | 346 passed; same 23 database tests skipped |
| `node --test scripts/docker-entrypoint.test.mjs` | 3 passed |
| `corepack pnpm lint` | Passed; same two warnings |
| `corepack pnpm exec next typegen` | Passed |
| `corepack pnpm exec tsc --noEmit` | Passed before and after build/development startup |
| `corepack pnpm build` | Passed using disposable database URL/auth secret |
| `corepack pnpm verify:change-order-pdf` | Passed; all six rendered pages inspected |
| `uv sync --locked` in backend | Passed with Python 3.12 |
| `uv run pytest -q --basetemp .pytest_cache/any638-<unique-id>` | 8 passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run python scripts/export_openapi.py --check ../contracts/openapi.json` | Passed |
| Local/legacy/Dokploy Compose validation | Passed, including resolved contexts and migration dependencies |
| Actual backend startup and HTTP liveness | 200 with exactly `{"status":"ok"}` |
| Standalone frontend through existing entrypoint | Started and passed HTTP smoke checks |
| Development startup from frontend | Passed |
| Relocated file/content audit | 170 existing files unchanged apart from line endings |
| Frontend lock package-version audit | No package versions changed |
| Original developer-file/environment hash audit | Unchanged; original next-env development references preserved in frontend |
| `git diff --check` | Passed |
| Independent review | No important actionable findings |

Focused deterministic tests cover project creation/edit/deletion, analysis and
regeneration, language separation, signed proofs, saved drafts and immutable
snapshots, Change Order export and evaluations. Nine additional auth checks
exercise real Next middleware/session signing and logout-cookie expiration.

HTTP smoke used frontend 3038 and backend 8038 to avoid existing local services;
the configured default ports remain 3000 and 8000. Frontend checks verified `/`,
`/login`, `/register`, public font/icon, unauthenticated 401 responses for
projects/analysis/drafts/evaluations, invalid login/register validation, locale
cookie setting and logout expiration. No database mutations were attempted.
The PDF fixture covers English, Spanish, German, Russian and long Russian text;
all six pages rendered correctly after relocation.

## Deployment checks and limitations

Executed from root:

```sh
docker compose -f compose.yaml --profile app config --quiet
docker compose -f docker-compose.yml --profile app config --quiet
docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet
docker build -t scope-guard-backend:any638 backend
git diff --check
```

Resolved Compose models confirm frontend/backend contexts, 3000/8000 local port
separation, the frontend's successful Drizzle migration gate, preserved named
PostgreSQL volume, and no backend database dependency or credentials.

### Fresh review verification вЂ” 2026-10-09

The earlier daemon-unavailable limitation is superseded for the backend: image
`scope-guard-backend:review` built successfully before this review. This review
started that image with no environment or database configuration, publishing
container port 8000 on an automatically assigned loopback port (63720).
`GET /health/live` returned HTTP 200 and exactly `{"status":"ok"}`.
The temporary container was stopped and removed in cleanup. No database,
migration or additional application service was started for this verification.

All seven requested frontend commands were repeated successfully with Corepack
pnpm 10.34.1, disposable process DATABASE_URL/AUTH_SECRET, and no OpenAI key or
TEST_DATABASE_URL. The owned frontend/node_modules already used pnpm 10.34.1;
frozen installation completed without deleting or replacing dependencies.
Observed results: 346 tests passed, 23 database tests skipped; 3 entrypoint tests
passed; lint passed with the same two warnings; Next type generation, TypeScript
and production build passed. Focused deterministic coverage includes auth,
projects, analysis/regeneration and saved drafts; no live-provider or authenticated
browser claim is made.

Backend locked installation, 8 pytest tests, Ruff lint/format and generated
OpenAPI freshness all passed again. All three Compose definitions validated.
Integrated Compose startup and the frontend container were not repeated in this
review. Earlier authenticated local startup exposed a missing drafts relation;
this schema drift remains unresolved, and login-page success does not establish
workspace readiness. No existing application database was modified.

The canonical plan is
[plans/2026-10-09-any-638-frontend-backend-foundation.md](plans/2026-10-09-any-638-frontend-backend-foundation.md).
The ignored root AGENT.md now documents boundaries, invariants, configuration,
validation, migration follow-ups and the approved local-checkout workflow.
Shared AGENTS.md and plans/README.md establish the canonical plans directory.

No disposable PostgreSQL was available, so the 23 mutating persistence tests
remain skipped locally. CI provisions a dedicated disposable PostgreSQL service.
Existing application databases were not used for test migrations/truncation.
No live OpenAI calls or authenticated browser journeys were performed. Existing
middleware deprecation and Vite config-loader notices remain unchanged.

## Setup and configuration changes

Frontend commands now run from `frontend/`. Supply local Next.js/Drizzle settings
in `frontend/.env.local` or `frontend/.env`, using its example. Original root
environment files were left untouched; secrets are not automatically copied.
Root `.env*` files continue to supply local Compose app-container configuration,
with frontend env files taking precedence and Compose overriding DATABASE_URL
to the internal PostgreSQL service. Backend configuration is optional under
`backend/.env` or prefixed process variables.

Root developer workspace/launchers/override/certificates remain unchanged.
The ignored handoff was intentionally updated during this review. Application commands explicitly select canonical Compose to avoid
silently loading the local legacy override. Installed root dependencies remain
after Windows denied their rename; independent frontend dependencies were
installed successfully. Generated outputs and environments are ignored.

The old lock omitted a Hono override already declared in package.json and failed
frozen installation under required pnpm 10.34.1. Normalizing it adds that override
and updates peer snapshot representation without changing package versions.

Exact current setup, startup, container and verification commands are in root
README.md. Dokploy remains standalone, using shared service definitions, and
continues directing business traffic to Next.js.

## Follow-up ownership

- ANY-639: agreed data/contracts design, SQLAlchemy/PostgreSQL lifecycle,
  compatible Alembic baseline and readiness; retain sole Drizzle ownership
  until an explicit handover.
- ANY-640: auth and existing business workflow/API migration, compatibility
  fixtures, frontend integration and deliberate endpoint routing cutover.
- ANY-641: document/PDF, scope extraction and currency services, with preserved
  historical values, languages, editable fields and deterministic verification.

- ANY-642: reassess remaining integrated runtime/deployment/verification gaps;
  this backlog follow-up is not an automatic product-work gate.

## Staging review

Stage only the relocation, foundation, Compose/CI/contracts and scoped docs.
Keep pre-existing local .gitignore additions unstaged, and root dev.sh, docker-compose.override.yml, pnpm-workspace.yaml and
test_openai.mjs untracked. Root AGENT.md, secrets, dependencies, caches,
certificates and generated test output remain ignored. The final index audit found 175 frontend renames (171 exact-content renames),
plus two instruction-document copies and scoped additions/updates. The cached
whitespace check passed. Only .gitignore has unstaged differences; the four root
local files listed above remain untracked. next-env content was preserved from
the pre-build snapshot and has no remaining unstaged difference. The root
/AGENT.md ignore rule was confirmed; frontend/AGENTS.md is tracked and not ignored.
