#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root/frontend"

corepack pnpm install --frozen-lockfile
(cd "$root/backend" && uv sync --locked --all-packages --all-groups --python 3.12)
node "$root/ci/scripts/check-gateways.mjs" --suite frontend
corepack pnpm lint
corepack pnpm api:types:check
corepack pnpm exec tsc --noEmit
corepack pnpm build
node "$root/ci/scripts/check-gateways.mjs" --suite auth-gateway
node "$root/ci/scripts/check-gateways.mjs" --suite generation-gateway
node "$root/ci/scripts/check-gateways.mjs" --suite drafts-gateway
corepack pnpm exec tsc --noEmit
