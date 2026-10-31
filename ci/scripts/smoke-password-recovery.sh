#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
# Tags share the fresh CI images; no duplicate build or runtime environment.
docker tag scope-guard-backend:ci scope-guard-api:any782
docker tag scope-guard-frontend:ci scope-guard-frontend:any782
docker build -f backend/tests/integration/storage-server.Dockerfile -t scope-guard-s3-test:release20250422 .
trap 'uv run --no-sync --package scope-guard python backend/scripts/verify_password_recovery.py stop || true' EXIT
uv run --no-sync --package scope-guard python backend/scripts/verify_password_recovery.py start
uv run --no-sync --package scope-guard python backend/scripts/verify_password_recovery.py check
