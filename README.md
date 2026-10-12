# Scope Creep Guard

Scope Creep Guard runs as a Next.js frontend, a FastAPI backend, and PostgreSQL.
Runtime data flows `frontend -> backend API -> PostgreSQL`. Next.js owns the UI,
localization, page guards, editable document state, and the same-origin gateway.
FastAPI owns all 24 public API operations, PDF export, scope extraction, and database access.
Backend SQLAlchemy models and Alembic are the only active migration authority.

Implementation plans live in [docs/architecture/plans/](docs/architecture/plans/README.md).
See [application ownership](docs/architecture/ownership.md) for current boundaries.

```text
frontend/          Next.js source, assets, tests, tools and Dockerfile
apps/api/          FastAPI composition root, Dockerfile and guarded entrypoint
apps/worker/       Future service-only worker contract
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
configure `AUTH_SECRET` plus `SCOPE_GUARD_API_ORIGIN`. Configure the same auth
secret, `SCOPE_GUARD_DATABASE_URL`, and any `OPENAI_API_KEY` in `backend/.env`.
The frontend never receives database credentials.

API writes with an `Origin` header require an exact entry in
`SCOPE_GUARD_ALLOWED_ORIGINS`. `SCOPE_GUARD_API_ORIGIN` is a server-only FastAPI
target. Root `.env*` files configure Compose; keep secrets and certificates out of Git.

## Run locally

For the integrated stack:

```sh
docker compose up --build -d
```

Startup order is PostgreSQL health, API entrypoint migration under a database advisory lock, FastAPI
readiness, then Next.js. Stop it with:

```sh
docker compose down
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
node --test scripts/docker-entrypoint.test.mjs
corepack pnpm lint
corepack pnpm api:types:check
corepack pnpm exec next typegen
corepack pnpm exec tsc --noEmit
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
Next.js gateway.

PDF export supports saved drafts and unsaved edits without implicit saving. Scope
uploads accept TXT, Markdown and text PDFs up to 5 MiB, 200 pages and 100,000 UTF-16
units; extracted text remains editable before saving. Monetary strings retain their
entered precision; changing currency performs no conversion or rate lookup.
See [ANY-641 verification](docs/architecture/any-641-verification.md). ANY-642 can
reassess proxy topology, integrated journeys and production resource budgets.

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
