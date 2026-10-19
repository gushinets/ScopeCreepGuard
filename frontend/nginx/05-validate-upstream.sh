#!/bin/sh
set -eu
case "${SCOPE_GUARD_API_ORIGIN:-}" in
    http://*|https://*) ;;
    *) echo 'Invalid API upstream origin' >&2; exit 1 ;;
esac
upstream_authority="${SCOPE_GUARD_API_ORIGIN#*://}"
case "$upstream_authority" in
    ''|*[!a-zA-Z0-9.:-]*) echo 'API upstream must contain only an origin, without credentials or a path' >&2; exit 1 ;;
esac
