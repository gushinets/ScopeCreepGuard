#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root/backend"

uv sync --locked --all-packages --all-groups --python 3.12
uv run pytest --require-integration
uv run ruff check . ../apps/api
uv run ruff format --check . ../apps/api
uv run mypy src/scope_guard ../apps/api/src/scope_guard_api
uv run mypy --platform win32 src/scope_guard ../apps/api/src/scope_guard_api
"$root/ci/scripts/check-contracts.sh"
sudo apt-get update
sudo apt-get install -y poppler-utils
uv run python scripts/verify_any641_pdf.py
