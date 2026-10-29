# CI structure

`.github/workflows/ci.yml` dispatches setup and verification from this directory.
The protected `rebase` job is retained. `actions/` pins Node/pnpm and Python/uv;
`contracts/openapi.json` records the API contract.

`check-containers.sh` validates full/component/Dokploy Compose contracts, builds
API, both worker roles and Nginx from the current revision, and checks retained
proxy/auth/upload/PDF behavior. `smoke-compose.sh` builds the fixed-source S3 test
fixture and runs `backend/scripts/verify_docker_startup.py` against those images.

The lifecycle harness selects `deploy/compose.yaml` and the documented
`deploy/compose.*.yaml` entry points explicitly. Configuration checks also verify
root/deploy bare-command parity and automatic root `.env` loading using a copied
fixture with synthetic values. The lifecycle harness selects empty test files through
`SCOPE_GUARD_LOCAL_ENV_FILE`, `SCOPE_GUARD_LOCAL_OVERRIDE_ENV_FILE` and
`SCOPE_GUARD_BACKEND_ENV_FILE` to avoid loading developer settings, supplies synthetic
settings, and uses UUID `scg-startup-test-*` projects. It never overrides migration
targets in release startup. Explicit historical targets are used only to prepare
previous-release fixtures. It verifies component closures, full readiness,
onboarding, locking/termination/failure gates, volume preservation and update
sequencing, plus Mailpit SMTP contents and persistence after restart.
Mailpit is verified by an isolated standard-library SMTP client, without public
application endpoints or external delivery. Disposable named volumes are retained;
removal requires explicit authorization. Container/network cleanup is restricted to the generated test project and labelled
storage fixture. No paid provider jobs are submitted.

Backend integration tests create their own PostgreSQL containers/databases.
`check-frontend.sh` runs the React suite, module boundaries, contract freshness,
types and build. The compatibility `verify_react_compose.py` delegates to the same
full lifecycle harness rather than constructing a modified service graph.
