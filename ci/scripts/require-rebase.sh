#!/usr/bin/env bash
set -euo pipefail

base="${1:-main}"
head="${2:-HEAD}"

# Only configured PR targets have a synchronization policy.
case "$base" in
  main|codex/any-758-email-verification-password-reset) ;;
  *) echo "Unsupported PR base: $base" >&2; exit 1 ;;
esac

git fetch --no-tags origin "+refs/heads/$base:refs/remotes/origin/$base"
base_sha="$(git rev-parse --verify "refs/remotes/origin/$base^{commit}")"
head_sha="$(git rev-parse --verify --end-of-options "$head^{commit}")"
if ! git merge-base --is-ancestor "$base_sha" "$head_sha"; then
  echo "PR head must include the current base: $base" >&2
  exit 1
fi

# Main keeps its linear-history policy. Integration task branches may merge
# updates from their integration base; the other jobs test the PR merge state.
if [[ "$base" == main ]] && [[ -n "$(git rev-list --merges "$base_sha..$head_sha")" ]]; then
  echo "PRs targeting main must not introduce merge commits" >&2
  exit 1
fi
