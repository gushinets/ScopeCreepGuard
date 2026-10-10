# ANY-642 Alembic handover verification

Date: 2026-10-11. Branch: `codex/any-642-alembic-handover`. Parent:
`649d5f0b627c3a8e21fd1f9149715ceb4c93a867` from
`origin/codex/any-640-fastapi-business-workflows`.

All mutating database checks used uniquely named, volume-free PostgreSQL 17
containers and disposable databases. No developer or application database was
selected.

## Migration behavior

- Focused Alembic/schema integration: 18 passed in 27.54s before the final
  unknown-schema case; final focused baseline suite, including ledger hash
  drift rejection: 7 passed in 10.21s.
- Fresh migration image smoke: the backend migration image ran twice against one
  disposable database, printed `migration_complete` both times, and PostgreSQL
  reported `0001_existing_drizzle_schema` at head.
- Concurrent migration-image smoke: two jobs started together, both exited 0 and
  printed `migration_complete`; the advisory lock serialized them and the database
  finished once at `0001_existing_drizzle_schema`.
- Legacy coverage validates the historical ledger and complete schema before
  explicit adoption, preserves all seeded rows and the ledger, stamps the
  baseline, upgrades to head, and repeats safely. Missing adoption permission,
  schema drift, partial schemas, extra public objects, unknown user schemas, and
  malformed ledger/revision states are rejected without stamping.

## Backend

- Final full `pytest --require-integration`: 375 passed in 66.48s with one inherited
  Starlette/httpx deprecation warning. The first full attempt reached 371 passed
  but two OpenAPI tests could not access the host pytest temp root; rerunning with
  a new workspace-owned `--basetemp` produced the passing result.
- Ruff lint: passed. Ruff format check: 148 files formatted. Mypy: no issues in
  80 source files, with four existing unchecked-body notes. OpenAPI freshness:
  passed.

## Frontend and integration harnesses

- Frontend unit suite: 41 files and 294 tests passed. The Vite native-loader
  compatibility warning remains inherited.
- Docker entrypoint: 3 passed. TypeScript, generated API freshness, Next route
  type generation, and lint passed; lint retains one inherited unused-variable
  warning in `lib/llm/schema.test.ts`.
- Updated frontend CI harness: 41 files / 294 tests plus 20 Python HTTP contract
  tests passed against owned Alembic-initialized databases.
- Auth/project gateway: 15 auth and 14 project checks passed. Generation and
  draft gateway harnesses passed their ownership, persistence, isolation,
  historical-context, and rate-limit checks.

## Containers and configuration

- Backend migration, backend runner, and frontend runner images built
  successfully. The frontend production build compiled and generated all routes
  without a database build argument.
- `compose.yaml`, compatibility `docker-compose.yml`, and standalone
  `docker-compose.dokploy.yml` validated successfully.
- The migration job is backend-built and startup ordering is PostgreSQL health,
  migration completion, backend health, then frontend.

## Limitations and follow-up

- The requested fresh-context review could not start because the workspace had
  no remaining agent credits. The implementer completed a separate whole-diff
  self-review and tightened legacy ledger validation based on that pass.
- No production database migration or deployment was performed. Operators must
  schedule the legacy schema freeze, verify backup/restore, enable the explicit
  adoption flag for one run, and remove it after success.
- ANY-641 retains PDF export, scope extraction, and currency-service migration.
  Later runtime work may reassess proxy topology and broader production hardening.
