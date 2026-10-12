# CI structure

`.github/workflows/ci.yml` is the GitHub dispatcher. It keeps the protected
`rebase` job name while delegating setup and verification to this directory.

- `actions/` pins the Node/pnpm and Python/uv toolchains.
- `ci/contracts/openapi.json` is the generated FastAPI contract snapshot.
- `scripts/` owns CI orchestration. Application runtime scripts remain with the
  application that owns them.

`smoke-compose.sh` always creates a `scopecreepguard-ci-*` Compose project,
uses anonymous host ports and a synthetic authentication secret, and removes
only that project's containers, volumes, and orphans.
