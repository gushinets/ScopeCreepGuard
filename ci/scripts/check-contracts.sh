#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

(cd "$root/backend" && uv run --no-sync python scripts/export_openapi.py --check ../ci/contracts/openapi.json)
(cd "$root/frontend" && corepack pnpm api:types:check)
