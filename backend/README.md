# Backend library

Python 3.12 / uv 0.11.19. The root uv workspace installs this library and the
separate apps/api distribution. From backend:

```sh
uv sync --locked --all-packages --all-groups --python 3.12
uv run python -m scope_guard.database.startup --database-url-env SCOPE_GUARD_DATABASE_URL
uv run uvicorn scope_guard_api.main:app --host 127.0.0.1 --port 8000 --reload --loop scope_guard.database.session:event_loop
uv run pytest --require-integration
uv run ruff check . ../apps/api
uv run ruff format --check . ../apps/api
uv run mypy src/scope_guard ../apps/api/src/scope_guard_api
uv run mypy --platform win32 src/scope_guard ../apps/api/src/scope_guard_api
uv run python scripts/export_openapi.py --check ../ci/contracts/openapi.json
```

Domain contains immutable types/rules and explicit repository contracts. Services
own use cases, read ports and explicit write UoWs. Database is the only SQLAlchemy
boundary; named query modules return detached read DTOs without ORM leakage.
Integrations implement provider, authentication and document interfaces. API
routes/schemas and concrete composition live in apps/api, never in this library.

Configuration retains SCOPE_GUARD_ names and DATABASE_URL/AUTH_SECRET/OPENAI_API_KEY
aliases. Native Settings supports optional .env. The migration service requires an
explicit SCOPE_GUARD_DATABASE_URL. API and workers do not run migrations. No import,
OpenAPI export, liveness or readiness check mutates schema. Readiness is a bounded
connectivity check with the existing sanitized 503 contract.

Alembic remains the only migration authority. Existing revisions and baseline
provenance are immutable. Empty/known-revision/explicit legacy-adoption guards
are preserved. Direct Alembic mutation is refused. The one-shot migration service
waits for PostgreSQL and holds advisory lock 642000001 on the transaction connection
through validation/upgrade/commit, bounded by a configurable 120-second lock wait.
Release startup resolves the single packaged head; explicit historical targets in
the CLI are reserved for staged operator transitions and disposable fixtures.
Unknown catalog/revision state fails without starting dependents or stamping schema.
See the root README for full/component Compose entry points and maintenance updates.
After reviewed legacy adoption, remove SCOPE_GUARD_ADOPT_LEGACY=true.

Tests own disposable PostgreSQL/Compose infrastructure. Never select an
application database or volume for verification. For checks without Docker,
select tests/unit, tests/api and tests/architecture. Preserve packaged fonts,
process limits, localized output, idempotency and historical snapshot semantics.
