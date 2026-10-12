# CI structure and Compose smoke

- **Branch:** `codex/ci-structure-and-compose-smoke`
- **Baseline:** local `019921056fb966c8915e21ce0711d4fbb07a32fe`, which contains
  fetched `origin/main` `aaff86ac379c3c6106150d15695bc18021d12c9d`.
- **Scope:** reorganize CI orchestration and the generated OpenAPI snapshot
  without changing application behavior, database schema, migration history or
  API contracts.

## Decisions

1. GitHub discovery remains limited to `.github/workflows/ci.yml`. It dispatches
   to `ci/actions` and `ci/scripts`, while retaining the protected visible
   `rebase` job.
2. The tracked FastAPI snapshot moves to `ci/contracts/openapi.json`; the export
   and frontend type generators continue to own its contents.
3. The former root `verify-any640` dispatcher is renamed
   `ci/scripts/check-gateways.mjs`. Backend application verification utilities
   remain with the backend because they exercise backend-owned runtime behavior.
4. The full-stack smoke script owns a uniquely named `scopecreepguard-ci-*`
   Compose project, uses anonymous host ports and synthetic CI-only values, and
   cleans only its own containers, volumes and orphans.
5. The existing local `compose.services.yaml` edit is included because it adds
   the required `app` `AUTH_SECRET` mapping and contains no other changes.

## Implementation and verification

1. Relocate the contract and CI-only root harness; add the local setup actions,
   check scripts, thin workflow dispatcher and CI README.
2. Update all runtime, generation, documentation and workflow references to the
   relocated contract and product-neutral gateway harness.
3. Validate shell syntax, contract/type freshness, all existing frontend and
   backend suites, static checks, Compose rendering and image builds.
4. Run the isolated Compose smoke and record actual results in the final commit
   and handoff.

## Verification record

- `uv sync --locked --all-packages --all-groups --python 3.12` and
  `corepack pnpm install --frozen-lockfile` passed.
- Frontend: 283 tests, 3 entrypoint tests, lint (one inherited warning), generated
  API types, Next route type generation, TypeScript and production build passed.
- Backend: 447 tests passed with disposable PostgreSQL integration coverage when
  run with `--basetemp .pytest_cache/ci-structure`; the host's shared pytest temp
  directory is access-denied. Ruff, formatting, normal MyPy and Windows-target
  MyPy passed; four inherited untyped-body notes remain.
- Contract freshness and frontend generated-type freshness passed; the snapshot
  content was not edited. All three Compose configurations rendered successfully.
- Backend and frontend images built, and the existing 11-check runtime image
  suite passed. Native Docker Desktop ran the same isolated full-stack flow as
  `smoke-compose.sh`: services became healthy, live/ready/login succeeded, and
  the CI-prefixed containers, network and volume were removed.

## Exclusions

No new feature, API shape, database migration, Alembic revision, queue, runtime
topology or protected-branch policy change is part of this work. No secrets,
environment files, local Docker resources, logs, output, certificates or ignored
`AGENT.md` are staged.
