#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
export SOURCE_REVISION="$(git rev-parse HEAD)"
(cd backend && uv sync --locked --all-packages --all-groups --python 3.12)
(cd backend && uv run --no-sync python scripts/verify_docker_startup.py --config-only)
docker build -f apps/api/Dockerfile --build-arg SOURCE_REVISION="$SOURCE_REVISION" -t scope-guard-backend:ci .
docker build -f apps/api/Dockerfile --target export-worker --build-arg SOURCE_REVISION="$SOURCE_REVISION" -t scope-guard-worker:ci .
docker build --target runner --build-arg SOURCE_REVISION="$SOURCE_REVISION" -t scope-guard-frontend:ci frontend
(cd backend && uv run --no-sync python scripts/verify_any641_runtime.py --containers --backend-image scope-guard-backend:ci --frontend-image scope-guard-frontend:ci)
(cd backend && uv run --no-sync python scripts/verify_react_proxy.py --image scope-guard-frontend:ci)
