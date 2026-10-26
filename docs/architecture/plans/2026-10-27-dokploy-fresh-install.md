# Dokploy clean production installation

- Request: deploy current main to `https://scopecreep.dokploy.gcexp.ru` with a
  new empty database; do not copy, migrate or delete the old production data.
- Base: main, `fde8fc31fde1b87e5662f9656340a15db07fa3e7`.
- Checkout: existing main; stage only this release's files. Preserve the existing
  proxy/E2E documentation edits and untracked QA files.
- Approved settings: GPT-6 Luna, input/output bounds `0.0000002`/`0.000001`
  USD per token, USD 5 per operation; retain the configured Squid forward proxy.
- Storage: pinned PGSTY Silo, private persistent export bucket, separate scoped
  application credentials. Disable paid background semantic review; retain local
  diagnostics. No automatic backups in this installation.

## Sequence

1. Remove provider calls from background diagnostics and update affected checks.
2. Add private Silo and idempotent bucket/user provisioning to the documented
   production Compose entry point. Check startup, private access and persistence.
3. Verify the full stack locally on unique disposable resources, with a synthetic
   provider key and no paid jobs; record source changes and built image identities.
4. Disable Dokploy auto-deployment before publishing release changes. Preserve the
   existing environment and deployment configuration for reference, without copying
   the database. Select a new PostgreSQL volume and production Compose entry point.
5. Build, stop the old application, initialize only the new empty database through
   the one-shot migration gate, then start storage, API, workers and frontend.
6. Verify public readiness, fresh registration, proxy/model access and private export
   storage. Keep the old PostgreSQL volume untouched.

## Evidence and limitations

- Read-only production check: PostgreSQL 17.11; two legacy Drizzle migrations,
  four public tables; 13 users, 16 projects, 58 history rows and 4 evaluation cases.
- Preparation read only the legacy database; no database copy, migration or
  deletion is part of this clean-install procedure.
- New production users must register again. Old data is not imported into the new
  database. The retained old volume is not a backup of future writes.
- Implemented: pinned Silo with separate scoped credentials and an idempotent
  private-bucket initializer; production maintenance waits for storage; background
  diagnostics retain local observations and perform no provider calls.
- Local checks: 28 focused unit/integration tests passed, Ruff and diff checks
  passed, production/component configuration checks passed. The complete eight
  service production topology initialized against a unique empty test database.
- HTTP smoke: frontend, registration, authenticated onboarding and project creation.
  S3: conditional upload, read/list/delete, anonymous/foreign-prefix rejection and
  persistence after a Silo restart. No paid provider calls were made.
- Local evidence: `output/dokploy-fresh-20261027/test-manifest.json` records the
  tested base, local source hashes, image IDs and revision labels; `pytest.xml`
  records the focused suite. Artifacts contain only synthetic test configuration.
- Existing production provider access: a read-only model lookup through the
  configured proxy returned HTTP 200 for `gpt-6-luna`.
- Server build/deployment outcomes are recorded separately in
  `output/dokploy-fresh-20261027/production-deployment.json`.
- Follow-up owner: this chat for the release; user for future backup destination.

## Dokploy domain compatibility follow-up

- Base: main `990177e8e80884696c6f50c3e1d3b88ecf8723f2`; branch
  `codex/dokploy-compose-services`, reviewed through a pull request.
- The first server build stopped before Docker execution: Dokploy 0.29.14 checks
  domain service names in the raw root file and does not expand `include` first.
- Declare a concrete, tag-free `app` at the root so Dokploy can inject domain
  labels and rewrite the file safely. Other roles keep their existing includes.
- Compare the complete resolved model with the authoritative component/production
  definitions, so the Dokploy frontend cannot silently drift from the shared one.
- Configuration parity passes on both Compose 2.24.0 and 5.6.1. The verifier sets
  the project directory explicitly for references written outside the repository.
- Preserve and disable obsolete Next.js file patches before rebuilding the Python
  and React release. Keep the prior database volume untouched.

## Python build bootstrap follow-up

- Base: main `a63d9b3fd4fde61664de01b0ea01a9d81bbad2f9`; branch
  `codex/uv-container-bootstrap`, reviewed through a pull request.
- Server build-only attempts stalled in `pip install uv==0.11.19`, including a
  host-network diagnostic. The old application and database stayed running.
- Copy the same uv version from Astral's official distroless image, pinned by
  its multi-platform digest. This removes the pip bootstrap download without
  changing Python dependencies, application code or runtime networking.
