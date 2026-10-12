# Application boundaries implementation plan

Approved in chat on 2026-10-12. Issue: ANY-637 migration umbrella.
Checkout workflow: current checkout, no worktree. Feature branch:
`codex/any-637-application-boundaries`. Fetched integration baseline:
`aaff86ac379c3c6106150d15695bc18021d12c9d` (`origin/main`). It includes
FastAPI, Alembic, document/extraction migration and platform correction;
no prerequisite cherry-picks are necessary. Preserve the three unrelated
root Markdown deletions, ignored AGENT.md and all local configuration.

## Decisions and target

- `apps/api/src/scope_guard_api`: main, bootstrap, dependencies, errors,
  transport parsers, schemas and existing routes. API package depends on backend.
- `backend/src/scope_guard/domain`: projects, analysis, drafts, change_orders,
  evaluations, auth, shared. Immutable values, validation and explicit ports;
  no HTTP, ORM, Alembic or external adapter imports.
- `backend/src/scope_guard/services`: projects, analysis, drafts, change_orders,
  evaluations, auth, documents, scope_extraction, health. Use cases, read ports,
  integration ports and explicit write transaction orchestration.
- `backend/src/scope_guard/database`: models/{base,users,projects,history,drafts,
  evaluations}, repositories/{projects,users,draft_persistence,evaluations},
  queries/{projects,drafts,history,evaluations,generation}, session,
  unit_of_work, migration_lock, cli, migrations, schema_verification and
  unchanged baseline_schema.json.
- `backend/src/scope_guard/integrations`: auth, llm, documents (including
  rendering, localization, scope readers and bounded isolated operations).
- `backend/core`: settings/logging only. Backend never imports API or frontend.
- `apps/worker/README.md`: future service-only worker/outbox contract, no runtime.
- Root uv workspace/lock; separate backend and API distributions. Frontend,
  contracts, Alembic history and font source assets retain ownership.

## Relocation manifest

All paths below start at backend/src/scope_guard unless otherwise stated.

| Source | Destination |
|---|---|
| main.py, api/* | apps/api/src/scope_guard_api; concrete wiring to bootstrap.py |
| modules/*/schemas.py | scope_guard_api/schemas; pure rules/constants extracted |
| modules/projects/{domain,repository}.py | domain/projects |
| modules/projects/use_cases.py | services/projects |
| modules/analysis/{domain,normalization,serialization}.py | domain/analysis |
| modules/analysis/{context,ports,use_cases}.py | services/analysis |
| modules/drafts/{domain,values,generation_context,serialization,repository}.py | domain/drafts |
| modules/drafts/use_cases.py | services/drafts |
| modules/change_orders/estimation.py | domain/change_orders |
| modules/change_orders/use_cases.py | services/change_orders |
| modules/change_orders/documents.py | services/documents/use_cases.py |
| modules/evaluations/{domain,repository,serialization}.py | domain/evaluations |
| modules/evaluations/use_cases.py | services/evaluations |
| modules/auth/repository.py | domain/auth/domain.py and repository.py |
| modules/auth/use_cases.py | services/auth; credentials to domain, ports to services |
| core/contracts.py | domain/shared enums/validators and API schemas/shared.py |
| core/js_compat.py | domain/shared/js_compat.py |
| infrastructure/database/* | database; split models and explicit read queries |
| database repositories drafts/generation | database/queries/generation.py |
| infrastructure/auth/* | integrations/auth |
| infrastructure/llm/* | integrations/llm; language.py to domain/shared |
| infrastructure/documents/* | integrations/documents |
| infrastructure/scope_readers/* | integrations/documents/scope_readers |
| infrastructure/technical/* | integrations/documents/technical |
| services/documents/{localization.py,labels.json} | integrations/documents |

Extract API business validation into domain validation. Split extraction wire
schemas from immutable service results. Services use injected adapters; health
routes use a service. Proof verification moves behind a service port. Preserve
ordered parsing, omitted/null semantics, all HTTP contracts, immutable history,
draft creation locks/idempotency, evaluation upsert and cascade behavior.

Update all backend tests/scripts/imports, Alembic env imports (not revisions),
workspace/package data, Compose variants, Docker builds, frontend Docker scripts,
CI, root verification launcher, README/backend/contracts/ownership/deployment
instructions and environment examples. Retain historical evidence. Remove old
api/main/modules/infrastructure paths and temporary facades at completion.

## Migration and runtime strategy

API image built from root, using apps/api/Dockerfile. Run from /app/backend;
Alembic config/revisions stay there. Entrypoint waits for connectivity (1s retry,
120s maximum), runs guarded CLI migrate with explicit SCOPE_GUARD_DATABASE_URL,
then execs Uvicorn. Invalid target/schema/adoption fails immediately. Signal
handling terminates migration children. No migrations on import/OpenAPI export.

Reuse transaction advisory lock 642000001 on the same connection as validation,
upgrade and verification. Wait without advisory-lock timeout, then restore 10s
DDL lock timeout. Commit/rollback releases lock. Replicas inspect state only
after acquiring it. Preserve all catalog/provenance/revision guards and explicit
legacy adoption. No schema revisions or changes.

Remove migrate service and profiles. Keep postgres/backend/app names, volumes,
health ordering, local 8000/3000 ports, internal http://backend:8000 gateway and
production internal backend. Standard command: docker compose up --build -d.
Migration locking does not distribute the generation limiter; retain one
production worker/replica. Workers never migrate or access ORM directly.

## Ordered commits and gates

1. Workspace, approved plan and API packaging shell; existing runtime works.
2. Domain separation and wire/rule split; existing runtime works.
3. Services/adapters, models/read queries and injected ports; existing API works.
4. API composition relocation, test/export paths and interim build compatibility.
5. Container migration startup, lock/wait behavior, Compose and CI.
6. Cleanup, architecture enforcement, complete verification and handoff.

Each commit must pass its focused checks and relevant existing suites. Temporary
forwarding imports are allowed only between commits. No unrelated staging.

## Verification

- Architecture transitive/lazy import checks; route service-only dependencies.
- Detached repository mapping, decimals and missing/null historical snapshots.
- Failing write use case rolls back intermediate changes on disposable PostgreSQL.
- Startup wait/migrate/server order, failures, adoption and signals; import/export
  causes no migration.
- Real concurrent lock held beyond 10 seconds; second waits, sees committed head;
  rollback/death releases lock.
- Isolated profile-free Compose startup, forwarding/auth, restart/concurrent API
  startup and migration failure. Never use existing application volumes.
- Existing full backend/frontend and gateway/contract/container suites; deterministic
  LLM doubles, disposable PostgreSQL only. Render/inspect PDF fixtures.

Commands: root `uv sync --locked --all-packages --all-groups`; Ruff check/format
over backend/apps/api. Backend `uv run --no-sync pytest --require-integration`,
Mypy over both packages on Linux/win32, export_openapi.py --check and
verify_any641_pdf.py. Frontend frozen pnpm install, tests, entrypoint tests,
lint, api:types:check, next typegen, tsc --noEmit and build. All three Compose
configs, both image builds, every verify-any640.mjs suite and ANY-641 image/runtime
checks. Preserve OpenAPI/type equality. Read installed Next guides before edits.

## Non-goals, risks and handoff

No features, database/schema change, queue, running worker, microservice,
production deployment, main changes or force push. Risks: ordered validation,
font/package data loss, isolated child imports, Alembic CWD, read mapping and
signal behavior. Final report: tree, branch/commit history, relocation list,
commands/results, debt and staging audit. Record actual evidence in
docs/architecture/application-boundaries-verification.md. Keep AGENT.md ignored.

## Execution ledger

- Setup: fetched baseline and created approved branch. Three unrelated deletions
  preserved. No prerequisite commits needed; main contains equivalent changes.
