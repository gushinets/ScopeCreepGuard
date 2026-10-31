#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root/backend"

uv sync --locked --all-packages --all-groups --python 3.12
task_branch="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-$(git branch --show-current)}}"
if [[ "$task_branch" == "codex/any-782-password-recovery" ]]; then
  # Keep ANY-782 out of the production LLM-worker integration execution lanes.
  uv run pytest --require-integration tests/unit tests/api tests/architecture \
    tests/integration/test_password_recovery.py tests/integration/test_recovery_limits.py \
    tests/integration/test_auth_tokens.py tests/integration/test_email_confirmation.py \
    tests/integration/test_release_migration.py tests/integration/test_schema_compatibility.py \
    tests/integration/test_migration_lock.py tests/integration/test_compose_startup.py
else
  uv run pytest --require-integration
fi
uv run ruff check . ../apps/api
uv run ruff format --check . ../apps/api
uv run mypy src/scope_guard ../apps/api/src/scope_guard_api
uv run mypy --platform win32 src/scope_guard ../apps/api/src/scope_guard_api
"$root/ci/scripts/check-contracts.sh"
sudo apt-get update
sudo apt-get install -y poppler-utils
uv run python scripts/verify_any641_pdf.py
