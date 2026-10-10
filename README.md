# Scope Creep Guard

One repository, two independently runnable applications. Next.js owns the frontend,
pending business workflows and PostgreSQL/Drizzle migrations. FastAPI owns authentication
(register, login, logout and me) and project list/create/get/update/delete through the Next.js same-origin gateway, plus
`GET /health/live`, returning HTTP 200 and `{"status":"ok"}` without integrations.
See [transitional ownership](docs/architecture/ownership.md).

Implementation plans live in [docs/architecture/plans/](docs/architecture/plans/README.md).
The [ANY-638 plan](docs/architecture/plans/2026-10-09-any-638-frontend-backend-foundation.md)
records implementation scope and links to dated verification evidence.

```text
frontend/          Next.js source, assets, tests, tools, Drizzle and Dockerfile
backend/           Python 3.12 src/scope_guard package, uv lock, tests, Dockerfile
contracts/         Generated FastAPI OpenAPI contract
tests/e2e/         Full user-journey verification
deploy/proxy/      Future route-by-route proxy boundary
docs/architecture/ Architecture and migration verification
compose.yaml       Local PostgreSQL and optional application stack
compose.services.yaml       Shared container definitions
docker-compose.dokploy.yml  Standalone production/Dokploy configuration
.github/workflows/          Application checks and existing rebase check
```

## Local configuration

Use Node >=22.13.0, pnpm **10.34.1**, Python **3.12**, uv **0.11.19**, and Docker
Compose >=2.24.0. Corepack selects pnpm from `frontend/package.json`.

Create `frontend/.env.local` from `frontend/.env.example` and provide your own
`DATABASE_URL`, `AUTH_SECRET` and `OPENAI_API_KEY`. Existing root `.env*` files are
not moved or copied automatically. Next.js now resolves `.env*` from `frontend/`;
Drizzle resolves `frontend/.env.local` before `frontend/.env`, preserving process
variable precedence. Root `.env*` configures Compose and remains supported as an
app container env file. Frontend `.env*` values override root env-file values in
local Compose, while Compose explicitly sets the internal database URL.

API writes with an `Origin` header require an exact entry in
`SCOPE_GUARD_ALLOWED_ORIGINS`, a JSON array configured in both services. The
frontend example includes local browser origins; local Compose derives them from
`FRONTEND_PORT`. Dokploy requires the public HTTPS origin allowlist explicitly.
Origin-less server clients remain supported. `SCOPE_GUARD_API_ORIGIN` is a
server-only forwarding target (internal backend address in Compose); routes
switch owners one slice at a time without retries or fallback writes.

Python starts without a database. Its optional `backend/.env` can contain
`SCOPE_GUARD_LOG_LEVEL=INFO` and `SCOPE_GUARD_DATABASE_URL` for connectivity
readiness; see `backend/.env.example`. Dokploy receives its
database/auth/OpenAI and optional outbound proxy settings from its environment
configuration. Never put local secrets, certificates or agent handoffs in Git.

## Run locally

From the repository root, start PostgreSQL if needed:

```sh
docker compose -f compose.yaml up -d postgres
```

From `frontend/`:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm db:migrate
corepack pnpm dev
```

From `backend/`, independently of PostgreSQL:

```sh
uv sync --locked --python 3.12
uv run uvicorn scope_guard.main:app --host 127.0.0.1 --port 8000 --reload --loop scope_guard.infrastructure.database.session:event_loop
```

Frontend uses port 3000; backend uses port 8000. Check
`http://127.0.0.1:8000/health/live`. Python `/docs` and `/openapi.json` are internal
tools for implemented Python routes. The four `/api/auth/*` operations and five project operations forward to Python; the remaining twelve operations, including legacy history creation, remain TypeScript-owned.
`/health/ready` checks PostgreSQL connectivity without writing schema; see the
[ANY-639 specification](docs/architecture/any-639-data-model-and-contracts.md).

## Verification

From `frontend/`:

```sh
corepack pnpm test
node --test scripts/docker-entrypoint.test.mjs
corepack pnpm lint
corepack pnpm exec next typegen
corepack pnpm exec tsc --noEmit
corepack pnpm build
```

`TEST_DATABASE_URL` enables the existing mutating persistence tests. Set it only
to a disposable database: those tests migrate and truncate their selected DB.
CI provisions a dedicated PostgreSQL service and never uses a deployed database.
The optional PDF visual command is `corepack pnpm verify:change-order-pdf` and
requires `pdftoppm`; outputs are ignored under `frontend/output/`.

From `backend/`:

```sh
uv sync --locked --python 3.12
uv run pytest --require-integration
uv run ruff check .
uv run ruff format --check .
uv run python scripts/export_openapi.py --check ../contracts/openapi.json
```

Generate the contract after implemented API changes:
`uv run python scripts/export_openapi.py --output ../contracts/openapi.json`.
For an inaccessible system pytest temp directory, use a **new, unused** directory:
`uv run pytest --basetemp .pytest_cache/verification-run-001`.
Backend integration tests require Docker and installed frontend dependencies.
They provision disposable PostgreSQL themselves and never select application
credentials. Drizzle retains migration ownership; there are no startup Alembic
operations. See backend/README.md for explicit preflight and safety boundaries.

## Containers and Dokploy

From the repository root:

```sh
docker compose -f compose.yaml --profile app config --quiet
docker compose -f compose.yaml --profile app up --build -d
docker compose -f compose.yaml --profile app down
docker build -t scope-guard-backend:local backend
docker run --rm -p 8000:8000 scope-guard-backend:local
```

The `app` profile starts PostgreSQL, the existing `migrate` runner, the Next.js
`app`, and `backend`. Frontend waits for successful Drizzle migration. Backend
does not depend on PostgreSQL and has its own HTTP health check. Override local
host ports with `POSTGRES_PORT`, `FRONTEND_PORT` and `BACKEND_PORT` in root `.env`.
Application scripts explicitly select `compose.yaml`, so ignored developer
`docker-compose.override.yml` files are not silently applied; select such local
overrides explicitly and review resulting ports/database URLs.

Dokploy continues to use `docker-compose.dokploy.yml` **by itself**, with shared
definitions supplied through Compose `extends`. Keep all root Compose files
available to deployment. Configure its domain to the **app** service, port 3000.
Backend is exposed internally on 8000; do not route the entire `/api` prefix to it.
The legacy `docker-compose.yml` includes the canonical local stack.

For mutating integration verification, select a separate Compose project and
unused host ports to create a disposable named volume. Never run verification
migrations or test truncation against an existing application database. Do not
use `down -v` on an existing application's stack.

## Next migration slices

- ANY-639: data/contracts design, Python PostgreSQL/SQLAlchemy integration,
  compatible Alembic baseline and database readiness; Drizzle remains authoritative.
- ANY-640: migrate authentication and business APIs with contract compatibility,
  explicit routing cutover and complete user-journey checks.
- ANY-641: document export, scope extraction and currency services under Python.

Existing research/plans document their historical layout. This README describes
current commands; no pricing, prompt, localization or UI redesign accompanies
the repository relocation.
