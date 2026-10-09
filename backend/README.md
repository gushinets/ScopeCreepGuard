# Backend foundation

Use Python 3.12 and uv 0.11.19. From this directory:

```sh
uv sync --locked --python 3.12
uv run uvicorn scope_guard.main:app --host 127.0.0.1 --port 8000 --reload
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/export_openapi.py --check ../contracts/openapi.json
```

GET /health/live returns 200 and `{"status":"ok"}` without external dependencies.
Configuration uses `SCOPE_GUARD_` environment variables and optional `.env`.
Only log level is configured; there are no required integration secrets.

Installations use committed uv.lock; `.venv` and caches are ignored. API transport
lives in api/routes; core owns configuration/logging. Future module, infrastructure
and service boundaries are documented in place. See root README for Docker,
generated OpenAPI and the current Next.js/Drizzle ownership boundary.
