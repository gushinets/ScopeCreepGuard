# ANY-642 Alembic Handover Implementation Plan

**Issue:** ANY-642 — Reassess and prepare integrated runtime, deployment and verification after the Python migration

**Base and branch:** `649d5f0b627c3a8e21fd1f9149715ceb4c93a867` from `origin/codex/any-640-fastapi-business-workflows`; implement on `codex/any-642-alembic-handover` in the existing checkout.

**Goal:** Make backend SQLAlchemy models and Alembic the only active PostgreSQL migration authority while safely supporting empty databases and explicit adoption of compatible legacy Drizzle databases.

**Architecture:** Runtime data flows from the frontend through FastAPI to PostgreSQL. A backend-owned one-shot migration container runs before the backend and frontend. It serializes execution, validates database state, initializes empty databases, or explicitly adopts a validated legacy schema before upgrading to Alembic head.

**Tech stack:** Python 3.12, SQLAlchemy 2, Alembic, psycopg, PostgreSQL 17, Docker Compose, Next.js 16.3, GitHub Actions.

## Global constraints

- Preserve unrelated untracked `dev.sh`, `docker-compose.override.yml`, `pnpm-workspace.yaml`, and `test_openai.mjs`.
- Do not use a worktree, modify `main`, or run migrations against a developer/application database.
- Keep ANY-641 PDF, scope extraction, currency, and unrelated UI/business work out of this branch.
- Use only disposable PostgreSQL 17 containers and unique databases for mutating verification.
- Preserve legacy application rows and the historical Drizzle ledger during adoption.
- Require an explicit `--adopt-legacy` flag for the first legacy cutover.

## Current state

- `backend/` contains canonical SQLAlchemy metadata, an immutable Alembic baseline, a frozen catalog manifest, strict schema comparison, and guarded disposable-only preparation commands.
- `frontend/` still contains Drizzle schema, migrations, configuration, runtime database helpers, migration scripts, dependencies, and a Docker migration stage.
- Compose starts a frontend-built Drizzle migration job before the frontend; the backend is not gated on migration completion.
- CI installs frontend dependencies in the backend job because backend integration tests replay Drizzle through Node.
- Docker requires `DATABASE_URL` in the frontend image build and frontend entrypoint although every public API operation is now Python-owned.
- Documentation still declares Drizzle as migration owner.

## Target architecture

`frontend -> backend API -> PostgreSQL`

`backend SQLAlchemy metadata + Alembic -> PostgreSQL`

The frontend has no database URL, ORM, migration code, migration dependency, or migration image. Application startup never mutates schema; a one-shot backend migration job must succeed before backend and frontend availability.

## Ordered implementation

### 1. Guarded production migration command

**Files:** alter backend migration CLI/helpers and migration tests.

- Add a single `migrate` operation that takes an explicitly named database URL environment variable.
- Reject URL query target overrides and inherited `PGSERVICE`, `PGSERVICEFILE`, `PGHOSTADDR`, and `PGPORT` before engine creation.
- Acquire a PostgreSQL transaction advisory lock with a bounded lock timeout.
- Classify state as empty, valid Alembic-managed, compatible legacy, or unknown/incompatible.
- Empty: upgrade to Alembic head, then validate.
- Compatible legacy: reject unless `--adopt-legacy`; validate, lock managed tables, revalidate, stamp the baseline, upgrade to head, then validate.
- Alembic-managed: accept only known revisions, upgrade to head, then validate.
- Repeat execution at head is a validated no-op. Any failure rolls back the transaction and exits nonzero with sanitized output.

### 2. Backend-owned legacy provenance

**Files:** move `frontend/drizzle/` SQL/journal provenance into backend test fixtures; alter integration support, manifest/provenance checks, and all disposable database setup.

- Retain historical Drizzle SQL only as immutable backend test input for constructing legacy databases.
- Replay historical SQL with psycopg rather than frontend Node/Drizzle packages.
- Initialize ordinary backend and gateway test databases through the guarded Alembic flow.
- Verify legacy rows and the inert `drizzle.__drizzle_migrations` ledger are byte/value-equivalent before and after adoption.

### 3. Retire frontend database ownership

**Files:** remove Drizzle config/migrations/schema/database helpers and retired persistence tests; alter frontend package/lockfile, Dockerfile, entrypoint, tests, and environment example.

- Remove `db:generate`, `db:migrate`, and `db:studio`, plus Drizzle dependencies.
- Remove the frontend migration Docker stage and all frontend database build/start configuration.
- Replace compatibility fixtures that directly access PostgreSQL with backend-owned disposable setup or API-bound assertions.
- Confirm no frontend runtime import reaches database code.

### 4. Runtime, CI, and deployment wiring

**Files:** alter backend Dockerfile, Compose variants, CI workflow, root environment example, and verification scripts.

- Add a backend migration image target/command using the same installed package and Alembic assets as the API image, without the API health check.
- Configure PostgreSQL healthy -> migration completed -> backend ready -> frontend start ordering.
- Pass `SCOPE_GUARD_DATABASE_URL` only to backend and migration services.
- Map `SCOPE_GUARD_ADOPT_LEGACY=true` to the explicit first-cutover flag; default false.
- Remove frontend database build arguments and CI's backend dependency on Node migration packages.

### 5. Documentation and handoff

**Files:** alter root README, architecture ownership/database docs, add an ANY-642 verification record, and update ignored `AGENT.md` without staging it.

- Describe Alembic as sole migration owner, the backend migration command/job, explicit legacy adoption, actual startup sequence, retry safety, failure behavior, and backup/restore rollback.
- Record branch inheritance `ANY-638 -> ANY-639 -> ANY-640 -> ANY-642`, this plan path, exact verification evidence, limitations, and follow-ups.

## Migration behavior

### Empty database

1. Acquire the migration advisory lock.
2. Confirm the managed public boundary contains no application objects or migration ledgers.
3. Run Alembic from base to head in the current transaction.
4. Validate the catalog and current revision; commit only on success.

### Legacy Drizzle database

1. Require `--adopt-legacy` / `SCOPE_GUARD_ADOPT_LEGACY=true`.
2. Confirm no Alembic revision exists and the historical Drizzle ledger has the frozen expected provenance.
3. Validate the entire managed schema, lock managed tables, and validate again.
4. Stamp `0001_existing_drizzle_schema`, upgrade to head, validate, then commit.
5. Preserve business rows and the Drizzle schema/ledger as inert provenance.

Unknown objects, partial schema, provenance drift, incompatible catalog state, malformed/unknown Alembic revisions, or lock timeout must fail without stamping or partial DDL.

## Rollback and failure behavior

- Migration runs transactionally and blocks dependent containers on failure.
- No automated destructive downgrade exists; the baseline downgrade remains refused.
- Application rollback restores images/routing without reversing a valid stamp or re-enabling Drizzle.
- Database recovery uses a reviewed backup/restore procedure. The first production adoption requires a migration freeze and verified backup outside this implementation task.

## Verification matrix

| Scenario | Required result |
|---|---|
| Fresh disposable PostgreSQL | guarded command reaches Alembic head, schema validates, repeat is unchanged |
| Populated legacy fixture | explicit adoption validates, stamps, upgrades, preserves all rows/ledger, repeat is unchanged |
| Legacy without flag | rejected before stamp |
| Partial/unknown/drifted schema | rejected without mutation |
| Unknown/malformed Alembic revision | rejected without upgrade |
| Concurrent runners/lock timeout | serialized success or bounded safe failure |
| Backend checks | full integration suite, Ruff lint/format, mypy, OpenAPI freshness |
| Frontend checks | tests, entrypoint tests, lint, API types, Next type generation, TypeScript, production build |
| Containers/configuration | backend/frontend images, migration job smoke, three Compose configurations |
| Repository hygiene | full diff review, `git diff --check`, staged diff check, unrelated files preserved |

## Handoff and follow-up ownership

- ANY-641 still owns PDF export redesign, scope extraction migration, and currency-service migration.
- Later ANY-642 work may reassess proxy topology, integrated user journeys, production hardening, and deployment operations beyond the minimum executable migration handover.
- No production migration or deployment is performed by this branch; operators must schedule the legacy freeze, backup, explicit adoption flag, and post-cutover flag removal.
