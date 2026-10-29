#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
# The harness selects deploy/compose.yaml explicitly and selects empty environment files for isolation.
# It uses UUID project names, synthetic settings and no paid jobs.
docker build -f backend/tests/integration/storage-server.Dockerfile -t scope-guard-s3-test:release20250422 .
(cd backend && uv run --no-sync python scripts/verify_docker_startup.py \
  --api-image scope-guard-backend:ci --frontend-image scope-guard-frontend:ci \
  --worker-image scope-guard-worker:ci)
