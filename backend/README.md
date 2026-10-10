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

Integration requires Docker and uses volume-free, harness-owned PostgreSQL 17
containers. Ordinary databases are initialized through Alembic; immutable SQL
fixtures recreate the retired Drizzle state only for legacy-adoption tests.
Tests never use application configuration; Docker failures fail the run. Select
tests/unit and tests/api without --require-integration for checks without Docker.
The selector event-loop factory above supports Psycopg on Windows.

SQLAlchemy models and Alembic are the sole migration source. Application startup
does not mutate schema. Run the guarded operational command with an explicitly
selected environment variable:

```sh
uv run python -m scope_guard.infrastructure.database.cli migrate --database-url-env SCOPE_GUARD_DATABASE_URL
```

For a verified legacy database, add `--adopt-legacy` during the one reviewed
cutover. The command validates schema and the historical ledger before stamping.
Exact mismatch or an unexpected revision rejects; direct Alembic mutation and
destructive baseline downgrade are refused. The old `check`, `upgrade-empty`, and
`adopt-baseline` operations remain test/preflight tools with disposable guards.

Installations use committed uv.lock; `.venv` and caches are ignored. API transport
lives in api/routes; core owns configuration/logging. Future module, infrastructure
and service boundaries are documented in place. See root README for Docker,
generated OpenAPI and the current frontend/backend ownership boundary.
