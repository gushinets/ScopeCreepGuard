# ANY-639 — Data contracts, PostgreSQL and Alembic implementation plan

> **For agentic workers:** Use superpowers:executing-plans, test-driven-development
> and verification-before-completion. Execute the six tasks in order and obtain
> one independent whole-branch review before the final commit/push.

**Goal:** Prepare Python persistence and contracts without changing the existing
Drizzle-owned schema, business traffic or application records.

**Architecture:** Async SQLAlchemy 2.0/Psycopg 3, explicit Unit of Work, exact
Alembic baseline, catalog compatibility checks and connectivity readiness.

**Tech stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2.0, Psycopg 3,
Alembic, uv 0.11.19, PostgreSQL 17 and pinned frontend tooling.

**Spec:** ../any-639-data-model-and-contracts.md. The user approved the in-chat
architecture, specification and task plan on 2026-10-09, then authorized execution.

## Global constraints

- Base: origin/codex/any-638-frontend-backend-foundation at
  9d317c391254ae06424c195536ab94e437d9cb3c; branch:
  codex/any-639-data-contracts-and-alembic. Use the approved existing checkout.
- Preserve unrelated .gitignore edits and untracked dev.sh,
  docker-compose.override.yml, pnpm-workspace.yaml and test_openai.mjs.
- Preserve all five tables, enums, defaults, named constraints, indexes and
  migration 0006 cascades. No redesign, new event table or immutable-JSON trigger.
- Preserve nullable legacy terms/snapshots, Decimal values, browser-local project
  email/end date, language metadata, complete-card PATCH and saved editable JSON.
- Drizzle stays the sole application migration owner. No automatic migrations,
  business API/auth migration, workers, application DB mutation or Linear writes.
- Audit/analytics is deferred to a separate approved task; its product decision
  remains open. Existing Vercel Analytics is unchanged.
- Tests mutate explicitly provisioned disposable PostgreSQL only. Never fall
  back to application DATABASE_URL or persistent Compose volumes.

## Review focus

1. Legacy null terms/snapshots stay readable without current-term substitution.
2. Same-named changed CHECK expressions fail compatibility before stamp.
3. Cancellation/failed commit cannot leak connections or leave partial writes.
4. CamelCase, missing/null and Decimal string representation match current API.
5. Test commands cannot accidentally select an application database.

## Task 1: Contracts and pure rules

- [x] Create core/contracts.py and module schemas for auth, projects/history,
  analysis, editable Change Orders/client materials, drafts and evaluations.
- [x] Create projects/domain.py (CommercialTerms), drafts/domain.py (protected
  field comparison), evaluations/domain.py (human-verdict resolution).
- [x] Write failing contract/domain tests and synthetic fixtures first; preserve
  casing, wrappers, timestamps, optionality, current limits and field selection.
- [x] New/update projects require complete hourly/fixed terms; active amount is
  positive, below 1e12 and at most two decimals. Inactive amounts become null.
- [x] Retain v1 saved documents, empty editable strings and legacy missing
  clientName/projectSnapshot. Snapshot claims from browsers remain untrusted.
- [x] Verify tests/unit/test_contracts.py and test_domain_rules.py, then suite.

## Task 2: Persistence mapping

- [x] Add locked SQLAlchemy asyncio, Psycopg binary, Alembic and direct Pydantic
  dependencies; create infrastructure/database/models.py.
- [x] Test/map UserRow, ProjectRow, HistoryEntryRow, DraftRow, EvaluationCaseRow
  with exact PostgreSQL definitions and enum values, not Python member names.
- [x] Test metadata and disposable-PostgreSQL defaults, JSONB/Decimal fidelity,
  nullable rows, uniqueness, checks and cascades. No business adapters yet.

## Task 3: Lifecycle, Unit of Work and readiness

- [x] Create session.py and unit_of_work.py. Database.new_uow() returns an
  async context manager; commit/rollback are explicit, exit without commit rolls
  back, reuse is rejected, sessions close and lifespan disposes the engine.
- [x] Configure optional secret SCOPE_GUARD_DATABASE_URL with lower-priority
  DATABASE_URL alias; never log URL/parameters/raw driver errors.
- [x] Create engine without connection at import/startup. Keep liveness exact.
- [x] Add /health/ready with 3-second overall deadline and no-store: 200
  {status:ok,database:ok}; missing/unreachable/timed-out DB gives 503
  {status:unavailable,database:unavailable}. Connectivity only, no schema writes.
- [x] Test aliases, sanitation, commit/rollback/failure/cancellation, separate
  sessions, pool return, shutdown and health recovery.

## Task 4: Baseline and guarded adoption

- [x] Create alembic.ini, alembic/env.py, script.py.mako and fixed revision
  0001_existing_drizzle_schema.py reproducing Drizzle journal 0000–0006.
- [x] Create schema_verification.py, migrations.py, cli.py and packaged
  baseline_schema.json from actual disposable Drizzle replay, with provenance.
- [x] Compare catalogs: exact types/nullability/defaults, numeric precision,
  enum order, keys/FKs/actions, CHECK expressions/validation, indexes and names.
  Ignore OIDs/column physical order; handle migration bookkeeping separately.
- [x] Guard online Alembic through injected connection. upgrade-empty rejects
  partial schema. adopt-baseline checks and stamps fixed revision on one
  transaction/connection under migration freeze/table locks. No purge/repair.
- [x] Same verified revision is a no-op; unexpected revision/drift rejects
  without schema/data/ledger writes. Baseline downgrade refuses table deletion.
- [x] Test independent Drizzle/baseline/metadata parity, populated preservation,
  every drift class and mutation-target safety using disposable databases.

## Task 5: Disposable harness and CI

- [x] Create tests/conftest.py, integration/support.py and safety tests. Harness
  owns ephemeral PostgreSQL 17 and distinct reference/fresh/adoption/drift DBs.
- [x] Seed two users, hourly/fixed/null projects, standalone history, v1/legacy
  drafts, Unicode and linked/unlinked evaluations. Compare all rows and ledger.
- [x] CI runs integration explicitly and cannot silently skip it; pinned Node/
  pnpm tooling replays actual Drizzle. Existing frontend CI stays disposable.

## Task 6: Packaging and handoff

- [x] Package Alembic/manifest in backend Docker image, pass explicit prefixed
  DB configuration in supported Compose entrypoints, preserve Drizzle runner
  and Next business routing. Backend has no migration startup hook.
- [x] Generate contracts/openapi.json (only new Python route is health/ready).
- [x] Write data dictionary/ER/contracts/validation, operations and factual
  verification docs; update ownership/backend READMEs and ignored AGENT.md.
- [x] Verify pytest, Ruff, generated OpenAPI, existing frontend tests/lint/type/
  build, all Compose configs, image liveness and disposable-DB readiness.
- [x] Obtain whole-branch review, address substantive findings with regression
  tests, stage issue-owned files only, commit and push the approved branch.

## Ownership, rollback and follow-ups

ANY-640 implements owner-scoped repositories/use cases, auth/proof adapters,
atomic draft workflow, HTTP compatibility and routing/E2E. ANY-641 implements
document/PDF, extraction and currency services. ANY-642 reassesses remaining
runtime gaps. Analytics/audit and production handover need separate approval.

Application rollback restores backend/config without reversing schema or
dropping tables. Later handover freezes schema changes, verifies backup/recovery,
finishes Drizzle, verifies/stamps, disables every Drizzle runner and enables one
Alembic runner. Preserve the old ledger. New Drizzle drift rejects stale adoption.

## Execution evidence

Progress, rulings and checks are recorded during implementation; the final
facts belong in ../any-639-verification.md. This file is the approved plan, not
proof of successful execution.
