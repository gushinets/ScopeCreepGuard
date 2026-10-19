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

`check-frontend.sh` checks the standalone React build and public module boundaries,
the unchanged OpenAPI snapshot/generated types and retained API gateway journeys.
`check-containers.sh` builds the unprivileged static Nginx image and FastAPI image,
checks actual proxy cookies/uploads/PDF/cancellation and runs
`backend/scripts/verify_react_compose.py` against the Compose service definitions.
That smoke uses its own project/database volume, enables the persistent schema,
disables provider calls, verifies a confirmed Draft save and removes its resources.
The required `rebase` job remains unchanged. No CI workflow contacts a paid provider.
