# ANY-638 вЂ” Frontend/backend foundation implementation plan

Issue: **ANY-638 вЂ” Reorganize the repository into frontend/backend applications
and initialize FastAPI**. The current Linear description defines scope; ANY-637
supplies migration context. Review checkpoints below do not change that scope.

## Baseline and approved workflow

- Base commit: `753c88af7f2b647e3bc52f750db4d5b5d17aa03e`.
- Current branch checkpoint: `codex/any-638-frontend-backend-foundation`.
- The user explicitly approved work in the existing local checkout, superseding
  the original worktree preference. Continue here; no worktree is required.
- This review does not switch branches, fetch, rebase, stash, reset, clean,
  recreate existing source, commit or push. Inspect actual Git state before
  future work; the checkpoint does not replace Git as the source of truth.
- Before relocation, frontend checks passed: 337 tests, TypeScript and production
  build; ESLint had two existing warnings. The 23 database tests were skipped.

## Scope and boundaries

Move existing Next.js source, assets, tests, package/lock/configuration, scripts
and Drizzle history to frontend. Initialize a separate Python 3.12 src-layout
scope_guard package with uv, FastAPI/Uvicorn, settings, logging, pytest and Ruff.
Liveness returns HTTP 200 and exactly {"status":"ok"} without integrations.

Preserve every existing Next.js API, auth/page guard, database operation, Drizzle
migration, prompt, pricing rule, localization flow, saved draft/proof/snapshot,
PDF helper and evaluation export. Prepare documented feature/module boundaries
without rewriting the UI or adding fake business endpoints.

Shared foundations include generated FastAPI OpenAPI, E2E/proxy boundaries,
shared Compose service definitions, standalone Dokploy support and CI. Current
business traffic stays with Next.js; never switch the entire /api prefix now.
High-level architectural ownership remains in [ownership.md](../ownership.md).

Excluded: Python database connectivity, SQLAlchemy/Alembic, migration handover,
auth/business API migration, PDF/extraction/currency implementations, workers,
queues, product redesign, new pricing formulas and real-provider test calls.

## Ordered implementation and review steps

1. Inspect issue context, instructions and original Git state; record the main
   baseline. Preserve unrelated files and credentials. Completed initially;
   this review inspected current state without fetching or switching branches.
2. Relocate the frontend and retain app-relative imports, font/assets, Drizzle
   paths and standalone startup behavior. Preserve root repository instructions.
3. Initialize FastAPI application creation, settings/logging and health routing.
   Add real API/configuration tests first and version uv.lock; ignore environments.
4. Integrate frontend/migration/backend Docker contexts and shared Compose
   definitions. Preserve local and Dokploy startup/routing/migration ownership.
5. Generate the health-only OpenAPI from FastAPI; add CI and concise responsibility
   documents. Keep all existing business logic in the relocated frontend.
6. Resolve frontend dependency verification through pinned Corepack pnpm 10.34.1.
   Inspect frontend/node_modules ownership first. Frozen installation succeeded
   without removing or recreating the dependency directory.
7. Re-run frontend/backend checks with disposable process configuration. Verify
   the existing backend image in a temporary container without any database;
   stop/remove only that verification container afterward.
8. Move this plan to the canonical directory, update ignored root AGENT.md and
   shared plan pointers, and stage only ANY-638 files. Keep unrelated local
   .gitignore and next-env edits unstaged. Confirm rename recognition and run
   git diff --cached --check; never commit automatically.

## Implementation rulings retained from the initial pass

- pnpm 10.34.1 normalized the lock's missing declared Hono override without
  changing package versions; peer snapshot representation changed.
- A frontend-local workspace isolates app installation from unrelated local
  workspace configuration at the repository root, which remains untouched.
- Windows denied a rename of the old installed root dependency directory;
  it was left in place and independent frontend dependencies were installed.
- Backend tests initially failed with the missing package and passed after
  implementation. Contract tests initially failed with the missing exporter.
- An inaccessible global pytest temp directory is handled with a fresh ignored
  workspace-local --basetemp; no existing temp/dependency directory is deleted.

## Verification commands and results

Run frontend commands from frontend using `corepack pnpm`, which selects the
manifest's pinned version. Configure DATABASE_URL and AUTH_SECRET only through
process variables with disposable values. Leave OPENAI_API_KEY and
TEST_DATABASE_URL unset for this review; use no local environment files.

| Command | Current review result |
| --- | --- |
| corepack pnpm install --frozen-lockfile | Passed; no dependency replacement |
| corepack pnpm test | 346 passed, 23 disposable-database tests skipped |
| node --test scripts/docker-entrypoint.test.mjs | 3 passed |
| corepack pnpm lint | Passed; same two existing warnings |
| corepack pnpm exec next typegen | Passed |
| corepack pnpm exec tsc --noEmit | Passed |
| corepack pnpm build | Passed with disposable process configuration |

Backend commands from backend: `uv sync --locked`, `uv run pytest`,
`uv run ruff check .`, `uv run ruff format --check .`, and
`uv run python scripts/export_openapi.py --check ../contracts/openapi.json`.
On this workstation pytest uses a unique `.pytest_cache/any638-review-<id>`
basetemp. Current review observed 8 tests passing and Ruff checks passing;
generated OpenAPI freshness passed. All three Compose definitions validated.

From root, validate Compose with `docker compose -f compose.yaml --profile app
config --quiet`, the docker-compose.yml compatibility entry point, and
`docker compose -f docker-compose.dokploy.yml config --no-interpolate
--no-env-resolution --quiet`. Run `git diff --cached --check` and
`git status --short` after staging.

Container runtime: existing image `scope-guard-backend:review` was started with
an automatically assigned loopback port and no integration configuration.
GET /health/live returned HTTP 200 with exactly {"status":"ok"}. The temporary
verification container was removed. No database or migration was started.

[Verification evidence](../any-638-verification.md) records dated command
results, stage audit and remaining limitations. It is evidence, not a second
implementation plan or architecture authority.

## Limitations and follow-up

The 23 mutating database tests remain skipped without an explicitly disposable
database. This review neither accesses application data nor applies migrations.
Earlier local startup exposed schema drift (missing drafts); login-page success
alone does not prove the authenticated workspace works. No live OpenAI or full
authenticated browser journey has been verified in this review.

- ANY-639: agree data/contracts, PostgreSQL/SQLAlchemy lifecycle and compatible
  Alembic baseline/readiness; Drizzle stays authoritative until explicit handover.
- ANY-640: migrate existing auth/business APIs with fixtures and deliberate routing.
- ANY-641: document/PDF, scope extraction and currency services.
- ANY-642: reassess remaining integrated runtime/deployment/verification gaps after
  migration. It is backlog follow-up, not an automatic gate on further product work.
