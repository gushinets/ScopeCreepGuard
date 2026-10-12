#!/bin/sh
set -eu

python -m scope_guard.database.startup --database-url-env SCOPE_GUARD_DATABASE_URL &
migration_pid=$!
trap 'kill -TERM "$migration_pid" 2>/dev/null || true; wait "$migration_pid" 2>/dev/null || true; exit 143' TERM
# POSIX asynchronous children may inherit ignored SIGINT; terminate explicitly.
trap 'kill -TERM "$migration_pid" 2>/dev/null || true; wait "$migration_pid" 2>/dev/null || true; exit 130' INT
wait "$migration_pid"
trap - TERM INT

exec "$@"
