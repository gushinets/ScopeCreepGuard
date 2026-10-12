#!/usr/bin/env bash
set -euo pipefail

base="${1:-main}"
git fetch origin "$base"
test "$(git merge-base HEAD "origin/$base")" = "$(git rev-parse "origin/$base")"
test -z "$(git rev-list --merges "origin/$base"..HEAD)"
