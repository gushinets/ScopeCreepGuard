#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

export AUTH_SECRET="ci-disposable-auth-secret-at-least-32-characters"
export OPENAI_API_KEY=""
docker compose -f compose.yaml config --quiet
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet
docker build -f apps/api/Dockerfile -t scope-guard-backend:ci .
docker build --target runner -t scope-guard-frontend:ci frontend
(cd backend && uv sync --locked --all-packages --all-groups --python 3.12)
(cd backend && uv run --no-sync python scripts/verify_any641_runtime.py --containers --backend-image scope-guard-backend:ci --frontend-image scope-guard-frontend:ci)
