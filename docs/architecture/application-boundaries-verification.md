# Application boundaries verification — 2026-10-12

Branch: `codex/any-637-application-boundaries`. Fetched baseline:
`aaff86ac379c3c6106150d15695bc18021d12c9d` (`origin/main`). This baseline already
contains equivalent ANY-641 technical migration/platform/audit commits; no
cherry-picks, reset, rebase, unrelated merge, main update or push was performed.
Approved plan: plans/2026-10-12-application-boundaries.md.

## Architecture and compatibility

FastAPI composition/routes/schemas are in apps/api; backend domain/services are
independent of HTTP/ORM/concrete adapters. Database owns mapped tables, explicit
repositories, UoWs and optimized read query implementations. Integration adapters
own auth, OpenAI/prompts, documents/fonts/localization and isolated scope readers.
Temporary old api/main/modules/infrastructure facades are removed.

API entrypoint waits for explicit PostgreSQL connectivity, takes existing
transaction advisory lock 642000001 on the Alembic connection, validates/upgrades,
commits/releases, and execs Uvicorn. Replicas wait past ten seconds safely and
revalidate committed state. Rollback and abrupt process death release the lock.
Failure does not start API. SIGTERM/SIGINT terminate migration children. No
migration occurs during application construction, health checks or OpenAPI export.

The default Compose stack has postgres/backend/app, no migrate service/profile.
It uses internal http://backend:8000 with local ports 8000/3000. Production backend
stays internal. The 24-hour startup health allowance permits long coordination
waits; successful readiness becomes healthy immediately. Migration failures exit
immediately. Alembic revisions, frozen fixtures and catalog provenance are
unchanged. All third-party lockfile versions were compared and preserved.

## Observed verification

| Commands (run from the indicated directory) | Observed result |
|---|---|
| Root `uv sync --locked --all-packages --all-groups` | Passed, 56 resolved workspace packages / 55 installed distributions |
| Backend `uv run --no-sync pytest --require-integration -q --basetemp .pytest_cache/boundaries-final` | **447 passed**, one inherited Starlette deprecation warning; disposable PostgreSQL/Compose only |
| Root `uv run --no-sync ruff check backend apps/api` and `ruff format --check backend apps/api` | Passed; 259 Python files formatted |
| Root Mypy over `backend/src/scope_guard apps/api/src/scope_guard_api`, normal and `--platform win32` | Both passed, 167 sources; existing untyped-body notes retained |
| Backend export_openapi.py `--check ../ci/contracts/openapi.json` | Passed; no contract content changes |
| Frontend frozen pnpm install | Passed using pinned 10.34.1 |
| Root `node ci/scripts/check-gateways.mjs --suite frontend` | **283 frontend tests / 40 files plus 20 compatibility checks passed** |
| Frontend `pnpm lint` | Passed; one inherited unused-variable warning |
| Frontend `pnpm api:types:check`, `pnpm exec next typegen`, `pnpm exec tsc --noEmit` | Passed; generated type content unchanged, canonical LF checkout declared |
| Frontend `pnpm build` | Passed, all existing routes compiled/generated |
| Frontend `node --test scripts/docker-entrypoint.test.mjs` | 3 passed |
| Root verify-any640.mjs suites `contracts`, `auth-gateway`, `generation-gateway`, `drafts-gateway` | Passed: contracts 20; auth/project journeys 15 + 14; generation/proof/draft save/list/edit/reload/dedup/ownership/history/limit scenarios passed |
| Root verify-any640.mjs `--suite containers` | Both images built; **11 connected/outage HTTP smoke checks passed**; owned containers removed |
| Backend verify_any641_runtime.py, native production gateway and `--containers --backend-image scg-any640-backend-check --frontend-image scg-any640-frontend-check` | **11 checks passed in each mode**; only owned disposable resources |
| Three Compose config commands (local, compatibility, Dokploy with no interpolation/env resolution) | Passed, no required profile |
| Backend verify_any641_pdf.py `--output ../output/pdf/application-boundaries` | Rendered **14 pages**: EN/RU/ES/DE, long/missing/oversized fixtures; all pages visually inspected, text/Unicode/page-flow intact |
| Git diff/staging audit and immutable-revision/fixture checks | Passed; no unrelated local data included |

New regression coverage includes transitive/lazy architecture imports, overridable
API service dependencies, detached domain mapping, failing-write rollback, target
guards/connectivity retries, migration failures, replica waiting beyond ten
seconds, rollback/process-death lock release, profile-free frontend integration,
restart/idempotent migration, concurrent replicas and entrypoint signal cleanup.

## Review, limitations and debt

Independent read-only review found no Critical/Important defects. Its separate
sandbox test attempt was interrupted after 18 passing dots; it is not counted as
a complete test result. The main final escalated suite above completed fully.
Aggregate get/document reads deliberately retain repository Work ports; list,
history/export/generation reads have dedicated query implementations. Central UoW
rollback is implicit on context failure; Work interfaces expose commit/context
cleanup rather than a public rollback method. These are documented future
refinement opportunities, not blockers for the requested boundaries.

Generation admission is still process-local: retain one production worker/replica.
No worker/queue/outbox table, schema revision, product behavior or live-provider
call was added. No standalone browser automation suite exists beyond the existing
UI and real gateway/runtime suites; those suites were retained and exercised.

Initial sandbox dependency/cache/process restrictions were resolved through
authorized escalated runs with owned temporary paths. A stale zero-byte Git lock
was removed only after confirming no Git process was running. The original
ten-second migration timeout and ignored background SIGINT were reproduced by
failing regressions before their fixes. A Compose harness stderr assertion and
Windows CRLF-generated-type freshness were corrected without weakening checks.

Unrelated local deletions remain unstaged: idea-006-scope-creep-guard-2026-05-25.md,
interface-generation-prompt-template.md and scope-creep-guard-prd.md. AGENT.md stays
ignored and uncommitted. Environment files, keys/certificates, logs, caches,
dependency folders, output PDFs/PNGs and scratch scripts are excluded. Tests never
migrated or modified an application database or existing application volume.

## Relocation/removal inventory

- `backend/src/scope_guard/api/*` and `main.py` -> apps/api/src/scope_guard_api.
- `modules/*/schemas.py` and wire conventions -> API schemas.
- Pure module domain/repository/validation/serialization rules -> backend/domain.
- Module use cases/analysis context/provider ports -> backend/services.
- Infrastructure database -> backend/database; models split without schema change;
  list/history/export/generation SQL moved to named query modules.
- Infrastructure auth/LLM/documents/readers/technical processes -> integrations;
  language rules -> domain/shared; telemetry -> core.
- Document localization/labels -> integrations/documents; process orchestration
  and interfaces -> services. Original packaged font/license bytes retained.
- backend/Dockerfile -> apps/api/Dockerfile; backend/uv.lock -> root workspace lock.
- Removed backend/.dockerignore, legacy modules/infrastructure/core JS bridges,
  generation/draft repository forwarding modules, duplicate document labels,
  separate Compose migration services and required app profiles.

## Final affected runtime tree

```text
ScopeCreepGuard/
├── pyproject.toml
├── uv.lock
├── .dockerignore
├── apps/
│   ├── api/
│   │   ├── src/
│   │   │   └── scope_guard_api/
│   │   │       ├── routes/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── drafts.py
│   │   │       │   ├── evaluations.py
│   │   │       │   ├── generation.py
│   │   │       │   ├── health.py
│   │   │       │   ├── locale.py
│   │   │       │   ├── projects.py
│   │   │       │   └── technical.py
│   │   │       ├── schemas/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── analysis.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── change_orders.py
│   │   │       │   ├── drafts.py
│   │   │       │   ├── evaluations.py
│   │   │       │   ├── projects.py
│   │   │       │   ├── scope_extraction.py
│   │   │       │   └── shared.py
│   │   │       ├── README.md
│   │   │       ├── __init__.py
│   │   │       ├── bootstrap.py
│   │   │       ├── cancellation.py
│   │   │       ├── contracts.py
│   │   │       ├── dependencies.py
│   │   │       ├── draft_cache.py
│   │   │       ├── draft_input.py
│   │   │       ├── errors.py
│   │   │       ├── evaluation_input.py
│   │   │       ├── generation_input.py
│   │   │       ├── generation_output.py
│   │   │       ├── history_input.py
│   │   │       ├── locale.py
│   │   │       ├── main.py
│   │   │       ├── origin.py
│   │   │       ├── project_input.py
│   │   │       ├── project_output.py
│   │   │       ├── requests.py
│   │   │       └── technical_input.py
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   └── pyproject.toml
│   └── worker/
│       └── README.md
├── backend/
│   ├── assets/fonts/ (original source fonts/licenses retained)
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/ (existing history unchanged)
│   ├── tests/
│   ├── scripts/
│   └── src/
│       └── scope_guard/
│           ├── core/
│           │   ├── __init__.py
│           │   ├── config.py
│           │   ├── logging.py
│           │   └── telemetry.py
│           ├── database/
│           │   ├── models/
│           │   │   ├── __init__.py
│           │   │   ├── base.py
│           │   │   ├── drafts.py
│           │   │   ├── evaluations.py
│           │   │   ├── history.py
│           │   │   ├── projects.py
│           │   │   └── users.py
│           │   ├── queries/
│           │   │   ├── __init__.py
│           │   │   ├── drafts.py
│           │   │   ├── evaluations.py
│           │   │   ├── generation.py
│           │   │   ├── history.py
│           │   │   └── projects.py
│           │   ├── repositories/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── draft_persistence.py
│           │   │   ├── evaluations.py
│           │   │   ├── projects.py
│           │   │   └── users.py
│           │   ├── README.md
│           │   ├── __init__.py
│           │   ├── baseline_schema.json
│           │   ├── cli.py
│           │   ├── migration_lock.py
│           │   ├── migrations.py
│           │   ├── schema_verification.py
│           │   ├── session.py
│           │   ├── startup.py
│           │   └── unit_of_work.py
│           ├── domain/
│           │   ├── analysis/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── domain.py
│           │   │   ├── normalization.py
│           │   │   ├── serialization.py
│           │   │   └── validation.py
│           │   ├── auth/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── domain.py
│           │   │   ├── repository.py
│           │   │   └── validation.py
│           │   ├── change_orders/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── constants.py
│           │   │   └── estimation.py
│           │   ├── drafts/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── domain.py
│           │   │   ├── generation_context.py
│           │   │   ├── repository.py
│           │   │   ├── serialization.py
│           │   │   ├── validation.py
│           │   │   └── values.py
│           │   ├── evaluations/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── domain.py
│           │   │   ├── evaluation_input.py
│           │   │   ├── repository.py
│           │   │   └── serialization.py
│           │   ├── projects/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── domain.py
│           │   │   ├── errors.py
│           │   │   ├── history_input.py
│           │   │   ├── repository.py
│           │   │   └── validation.py
│           │   ├── shared/
│           │   │   ├── __init__.py
│           │   │   ├── enums.py
│           │   │   ├── errors.py
│           │   │   ├── identifiers.py
│           │   │   ├── js_compat.py
│           │   │   ├── language.py
│           │   │   └── validation.py
│           │   └── __init__.py
│           ├── integrations/
│           │   ├── auth/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── draft_proofs.py
│           │   │   ├── passwords.py
│           │   │   └── sessions.py
│           │   ├── documents/
│           │   │   ├── assets/
│           │   │   │   ├── OFL-noto-sans.txt
│           │   │   │   ├── noto-sans-bold.ttf
│           │   │   │   └── noto-sans.ttf
│           │   │   ├── scope_readers/
│           │   │   │   ├── __init__.py
│           │   │   │   ├── pdf.py
│           │   │   │   └── text.py
│           │   │   ├── technical/
│           │   │   │   ├── __init__.py
│           │   │   │   ├── entry.py
│           │   │   │   ├── operations.py
│           │   │   │   └── windows_limits.py
│           │   │   ├── __init__.py
│           │   │   ├── extraction.py
│           │   │   ├── labels.json
│           │   │   ├── localization.py
│           │   │   ├── preparation.py
│           │   │   └── renderer.py
│           │   ├── llm/
│           │   │   ├── prompts/
│           │   │   │   ├── README.md
│           │   │   │   ├── __init__.py
│           │   │   │   ├── analysis-system-v1.txt
│           │   │   │   ├── analysis-user-v1.txt
│           │   │   │   ├── analysis_v1.py
│           │   │   │   ├── client-materials-v1.txt
│           │   │   │   ├── client_materials_v1.py
│           │   │   │   ├── reply-regeneration-v1.txt
│           │   │   │   └── reply_tone_skills_v1.py
│           │   │   ├── __init__.py
│           │   │   ├── language.py
│           │   │   ├── openai.py
│           │   │   ├── rate_limit.py
│           │   │   ├── retry.py
│           │   │   └── schemas.py
│           │   └── __init__.py
│           ├── services/
│           │   ├── analysis/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── context.py
│           │   │   ├── ports.py
│           │   │   └── use_cases.py
│           │   ├── auth/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── ports.py
│           │   │   └── use_cases.py
│           │   ├── change_orders/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   └── use_cases.py
│           │   ├── documents/
│           │   │   ├── __init__.py
│           │   │   ├── models.py
│           │   │   ├── ports.py
│           │   │   ├── rendering.py
│           │   │   ├── service.py
│           │   │   └── use_cases.py
│           │   ├── drafts/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── proofs.py
│           │   │   ├── queries.py
│           │   │   └── use_cases.py
│           │   ├── evaluations/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── queries.py
│           │   │   └── use_cases.py
│           │   ├── health/
│           │   │   ├── __init__.py
│           │   │   ├── ports.py
│           │   │   └── service.py
│           │   ├── projects/
│           │   │   ├── README.md
│           │   │   ├── __init__.py
│           │   │   ├── queries.py
│           │   │   └── use_cases.py
│           │   ├── scope_extraction/
│           │   │   ├── __init__.py
│           │   │   ├── models.py
│           │   │   ├── ports.py
│           │   │   ├── service.py
│           │   │   └── use_cases.py
│           │   ├── README.md
│           │   └── __init__.py
│           └── __init__.py
├── frontend/ (existing UI/gateway retained)
├── contracts/ (OpenAPI/type contents unchanged)
├── docs/architecture/
├── compose.services.yaml
├── compose.yaml
├── docker-compose.yml
└── docker-compose.dokploy.yml
```
