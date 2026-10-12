#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

project="scopecreepguard-ci-${GITHUB_RUN_ID:-local}-${RANDOM}"
if [[ "$project" != scopecreepguard-ci-* ]]; then
  echo "Refusing to manage a non-CI Compose project: $project" >&2
  exit 2
fi

export COMPOSE_PROJECT_NAME="$project"
export AUTH_SECRET="ci-disposable-auth-secret-at-least-32-characters"
export OPENAI_API_KEY=""
export SCOPE_GUARD_OPENAI_API_KEY=""
export POSTGRES_PORT=0
export BACKEND_PORT=0
export FRONTEND_PORT=0
response_headers="$(mktemp)"

cleanup() {
  status=$?
  if (( status != 0 )); then
    docker compose -f compose.yaml ps || true
    docker compose -f compose.yaml logs --no-color postgres backend app || true
  fi
  docker compose -f compose.yaml down --volumes --remove-orphans || true
  rm -f "$response_headers"
  exit "$status"
}
trap cleanup EXIT INT TERM

docker compose -f compose.yaml up --build -d

wait_healthy() {
  local service="$1"
  local identifier health
  for _ in $(seq 1 120); do
    identifier="$(docker compose -f compose.yaml ps -q "$service")"
    if [[ -n "$identifier" ]]; then
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$identifier")"
      if [[ "$health" == healthy ]]; then
        return 0
      fi
      if [[ "$health" == exited || "$health" == dead ]]; then
        echo "$service stopped before becoming healthy" >&2
        return 1
      fi
    fi
    sleep 1
  done
  echo "$service did not become healthy" >&2
  return 1
}

for service in postgres backend app; do
  wait_healthy "$service"
done

backend_port="$(docker compose -f compose.yaml port backend 8000 | sed 's/.*://')"
frontend_port="$(docker compose -f compose.yaml port app 3000 | sed 's/.*://')"
curl --fail --silent --show-error "http://127.0.0.1:${backend_port}/health/live" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:${backend_port}/health/ready" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:${frontend_port}/login" >/dev/null
curl --fail --silent --show-error --dump-header "$response_headers" \
  --header "content-type: application/json" \
  --data '{"email":"compose-smoke@example.test","password":"12345678"}' \
  "http://127.0.0.1:${frontend_port}/api/auth/register" >/dev/null
session_token="$(awk 'tolower($0) ~ /^set-cookie: scg_session=/ { sub(/\r$/, ""); sub(/^[^=]*=/, ""); sub(/;.*/, ""); print; exit }' "$response_headers")"
if [[ -z "$session_token" ]]; then
  echo "Registration did not issue a session cookie" >&2
  exit 1
fi
curl --fail --silent --show-error --header "cookie: scg_session=${session_token}" \
  "http://127.0.0.1:${frontend_port}/api/auth/me" >/dev/null

echo "Compose smoke passed for $project."
