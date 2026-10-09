# Python backend

Use Python 3.12 and uv 0.11.19. From this directory:

```sh
uv sync --locked --python 3.12
uv run uvicorn scope_guard.main:app --host 127.0.0.1 --port 8000 --reload --loop scope_guard.infrastructure.database.session:event_loop
uv run pytest --require-integration
uv run ruff check .
uv run ruff format --check .
uv run python scripts/export_openapi.py --check ../contracts/openapi.json
```

GET /health/live returns 200 and `{"status":"ok"}` without external dependencies.
Configuration uses `SCOPE_GUARD_` environment variables and optional `.env`.
Optional secret SCOPE_GUARD_DATABASE_URL takes precedence over DATABASE_URL.
GET /health/ready performs a bounded connectivity check: available PostgreSQL
returns 200; missing/invalid/unavailable PostgreSQL returns sanitized 503. It
performs no schema writes and is separate from exact schema verification.

Integration requires Docker and installed frontend dependencies, replaying the
real Drizzle migrator on a volume-free, harness-owned PostgreSQL 17 container.
Tests never use application configuration; Docker failures fail the run. Select
tests/unit and tests/api without --require-integration for checks without Docker.
The selector event-loop factory above supports Psycopg on Windows.

Drizzle remains the application migration owner. No automatic migration exists.
Read the specification at docs/architecture/any-639-data-model-and-contracts.md
from the repository root. Explicit read-only preflight:

```sh
uv run python -m scope_guard.infrastructure.database.cli check --database-url-env EXPLICIT_PREFLIGHT_URL
```

Preparation mutations require a harness-owned disposable target, the
SCOPE_GUARD_TEST_DATABASE_URL variable and --disposable, using upgrade-empty or
adopt-baseline in place of check. Never relabel application credentials to bypass
the guard. Exact mismatch/unexpected revision rejects; direct Alembic mutation
and destructive baseline downgrade are refused. Production ownership transfer
requires a separately approved task and migration freeze.

Installations use committed uv.lock; `.venv` and caches are ignored. API transport
lives in api/routes; core owns configuration/logging. Future module, infrastructure
and service boundaries are documented in place. See root README for Docker,
generated OpenAPI and the current Next.js/Drizzle ownership boundary.
