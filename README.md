# Scope Creep Guard

Scope Creep Guard runs as a React/Vite frontend, a FastAPI backend, and PostgreSQL.
Runtime data flows `browser -> Nginx /api -> backend API -> PostgreSQL`. React owns
the UI, localization, page guards and editable document state. Nginx serves static
assets and forwards API requests on the same public origin.
FastAPI owns public API operations, PDF export, scope extraction and database access.
Backend SQLAlchemy models and Alembic are the only active migration authority.

Implementation plans live in [docs/architecture/plans/](docs/architecture/plans/README.md).
See [application ownership](docs/architecture/ownership.md) for current boundaries.

```text
frontend/          React source, assets, tests, Vite and static Nginx Dockerfile
apps/api/          FastAPI composition root, Dockerfile and guarded entrypoint
apps/worker/       Durable export and LLM worker entrypoints
backend/           Pure domain, services, persistence, integrations and Alembic
pyproject.toml     Python workspace; root uv.lock pins both packages
ci/contracts/      Generated FastAPI OpenAPI contract snapshot
tests/e2e/         Full user-journey verification
docs/architecture/ Architecture plans and verification records
compose.yaml       Default PostgreSQL, API and frontend stack
compose.services.yaml       Shared container definitions
docker-compose.dokploy.yml  Standalone production/Dokploy configuration
```

## Configuration

Use Node >=22.13.0, pnpm 10.34.1, Python 3.12, uv 0.11.19, and Docker
Compose >=2.24.0. Create `frontend/.env.local` from `frontend/.env.example` and
configure `SCOPE_GUARD_API_ORIGIN` (defaults to http://127.0.0.1:8000 in development).
Configure `AUTH_SECRET`, `SCOPE_GUARD_DATABASE_URL`, and any `OPENAI_API_KEY` only
in the backend/worker environment. The browser uses `/api`; no browser tokens or
backend secrets are bundled. Do not prefix private settings with `VITE_`.

API writes with an `Origin` header require an exact entry in
`SCOPE_GUARD_ALLOWED_ORIGINS`. `SCOPE_GUARD_API_ORIGIN` is a server-only FastAPI
target. Root `.env*` files configure Compose; keep secrets and certificates out of Git.

## Run locally

The React application requires the persistent workflow and compatible
`0007_nonblocking_llm` schema. Before production cutover, follow the existing
[workflow rollout](docs/architecture/draft-workflow.md) backup/backfill/verification
procedure. Base Compose remains an infrastructure/legacy API smoke configuration;
it does not silently activate persistent workflows. With explicit disposable or
operator-approved database, private export storage and LLM configuration:

```sh
docker compose -f compose.yaml -f compose.workflow.yaml -f compose.llm.yaml up --build -d
```

Startup order is PostgreSQL health, API entrypoint migration under a database advisory lock, FastAPI
readiness, then Nginx on port 3000. Run API and worker images from the same release.
Restart `app` after replacing the backend container if its address changes: Nginx
resolves the configured upstream at startup. Stop the same stack with:

```sh
docker compose -f compose.yaml -f compose.workflow.yaml -f compose.llm.yaml down
```

For separate development, start PostgreSQL, then run the guarded migration from
`backend/` before starting the two applications:

```sh
docker compose -f compose.yaml up -d postgres
cd backend
uv sync --locked --all-packages --all-groups --python 3.12
uv run python -m scope_guard.database.cli migrate --database-url-env SCOPE_GUARD_DATABASE_URL
uv run uvicorn scope_guard_api.main:app --host 127.0.0.1 --port 8000 --reload --loop scope_guard.database.session:event_loop
```

From `frontend/`:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm dev
```

Frontend uses port 3000 and backend uses 8000. `/health/live` has no integration
dependency; `/health/ready` checks database connectivity without mutating schema.
Enable `SCOPE_GUARD_WORKFLOW_V2=true` and `SCOPE_GUARD_LLM_WORKFLOW=true` for the
API and run the existing LLM/export workers against that same development database.
From `backend/`, run `uv run python ../apps/worker/main.py` in separate terminals
with `SCOPE_GUARD_WORKER_ROLE=llm` and `SCOPE_GUARD_WORKER_ROLE=export` respectively.
See [worker configuration](apps/worker/README.md).
Vite forwards `/api` without changing the browser Origin. Production uses only
static assets: `docker build --target runner -t scope-guard-frontend frontend`.
Set `SCOPE_GUARD_API_ORIGIN` to the reachable FastAPI origin in the runtime container;
the Nginx entrypoint validates and substitutes this server setting. `pnpm start`
is a local preview, not the production server.

## Legacy database adoption

An empty database is initialized exclusively through Alembic. For a database
created by the retired Drizzle migrations, freeze schema changes and verify a
backup, then set `SCOPE_GUARD_ADOPT_LEGACY=true` for one API startup. The
startup runner validates the complete schema and historical ledger before stamping the
baseline. Unknown or incompatible states fail without stamping. Remove the flag
after adoption. Repeated runs at Alembic head validate and exit safely.

Alembic-managed databases must contain exactly one known revision from the
backend's local Alembic lineage. The guarded migration runner upgrades any such revision to
the configured head. Missing, malformed, multiple, foreign, or unknown revision
rows fail without mutation. The frozen Drizzle baseline comparison applies only
to legacy adoption and the baseline revision; future revisions use the
revision-aware backend validator.

No automatic destructive downgrade exists. Roll back application images without
reversing a valid stamp or re-enabling Drizzle; restore the database from a
reviewed backup when database recovery is required.

## Verification

Frontend:

```sh
corepack pnpm test
corepack pnpm lint
corepack pnpm api:types:check
corepack pnpm typecheck
corepack pnpm build
```

Backend:

```sh
uv run pytest --require-integration
uv run ruff check . ../apps/api
uv run ruff format --check . ../apps/api
uv run mypy src/scope_guard ../apps/api/src/scope_guard_api
uv run python scripts/export_openapi.py --check ../ci/contracts/openapi.json
```

Integration tests provision owned PostgreSQL 17 containers and unique databases.
The Compose startup test uses a uniquely named disposable volume, then removes
only that test stack. Never point test or migration verification at an application
database. Validate deployment configuration with all three Compose entry points.

Dokploy uses `docker-compose.dokploy.yml` by itself. Configure its public domain
for the `app` service on port 3000; FastAPI stays internal on 8000 behind the
Nginx gateway. Page routes use SPA fallback; unknown `/api` routes keep API errors,
missing assets return 404, HTML revalidates and hashed assets cache immutably.

The persistent frontend exports finalized History agreements as durable PDFs.
The retained legacy API also supports saved drafts and unsaved PDF previews.
Scope
uploads accept TXT, Markdown and text PDFs up to 5 MiB, 200 pages and 100,000 UTF-16
units; extracted text remains editable before saving. Monetary strings retain their
entered precision; changing currency performs no conversion or rate lookup.
See the [React migration record](docs/architecture/plans/2026-10-19-react-frontend-migration.md)
for current container/browser checks and the historical
[ANY-641 verification](docs/architecture/any-641-verification.md) for legacy API evidence.

The API entrypoint waits up to 120 seconds for PostgreSQL, then acquires the
existing transaction advisory lock (642000001) without a replica-wait timeout.
It validates and runs guarded Alembic on that same connection, commits/releases
the lock, then starts FastAPI. Schema/adoption failures stop the container. A
24-hour startup health allowance accommodates migration lock waits; a successful
readiness check becomes healthy immediately, without waiting for that allowance.
Entrypoint failures exit immediately and fail Compose dependency startup.

Generation admission remains process-local: production uses one API worker and
one replica. Migration concurrency safety does not change that restriction.
Deploy compatible frontend/API images together; rollback does not downgrade or
rewrite Alembic history. See the application-boundaries plan and verification
record for exact changes and test evidence.
