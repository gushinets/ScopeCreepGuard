# ANY-553 — bounded comparison CPU follow-up

## Checkout and decision

Base: b81cf7a; branch: codex/any-553-reply-similarity, existing checkout.
Initial tree was clean. Preserve linear ancestry from main 837bb5f; no worktree,
reset, stash or merge commit. The user authorized updating PR #34.

The user explicitly accepted skipping novelty checking above 2,048 normalized
characters and recording why. That supersedes the original requirement to check
every permitted reply for this length range. Raw reply allowance stays 32,768
characters. NFKC/casefold expansion also takes the skip path, even if the expanded
representation exceeds the raw length allowance. No truncation or alternate score.
The exact SequenceMatcher ratio and inclusive 0.72 threshold remain for shorter
replies. No frontend, public API, service, table or migration changes.

## Ordered implementation

1. Add matcher-forbidden tests for long repetitive text, equality and Unicode
   expansion; test the exact comparison length boundary and normalized length.
2. Separate raw reply length from the CPU comparison cap. Return explicit score
   and skip metadata; persist it through existing novelty checkpoints and reuse
   the same function in post-publication diagnostics.
3. Verify single-call publication and cached recovery for long replies, with
   original frozen input, structural rules and publication fences intact.
4. Run unit/API/architecture tests, disposable PostgreSQL recovery, static checks,
   OpenAPI freshness and the exact repository rebase script. Review the final diff.
5. Commit and push a normal follow-up to the existing PR. Inspect fresh GitHub
   checks without weakening scheduling or marking checks successful artificially.

## Verification evidence

- TDD: six long-input cases failed on the old implementation; all seven initial
  cap cases passed after implementation. A further Unicode expansion case failed
  before removing the normalized-length rejection and passed afterward.
- `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_reply_similarity.py
  -q -p no:cacheprovider --tb=short`: 39 passed in 17.18s.
- From backend: `../.venv/Scripts/python.exe -m pytest
  tests/integration/test_reply_similarity_recovery.py --require-integration
  -q -p no:cacheprovider --tb=short`: 11 passed in 127.24s. After changing only
  synthetic long-word fixtures to spaced text, final `-k long`: 2 passed in 47.94s.
  Owned disposable PostgreSQL and controlled provider responses only.
- Ruff lint and formatting: pass, 370 files unchanged by formatter.
- Both mypy modes: 229 sources, pass (existing untyped-function notes only).
- OpenAPI export freshness: pass. No public schema change.
- Exact `D:/Git/bin/bash.exe ci/scripts/require-rebase.sh main` from root: pass;
  main is 837bb5f. An earlier invocation from backend had an incorrect relative
  path and did not execute the gate; the root invocation is authoritative.
- Independent read-only review: no actionable findings, including Unicode expansion.
- `git diff --check`: pass. domain/drafts/workflow.py unchanged. AGENT.md and
  WORKLOG.md remain ignored and uncommitted.
- From backend: `../.venv/Scripts/python.exe -m pytest tests/unit tests/api
  tests/architecture -q -p no:cacheprovider
  --basetemp=D:/Devpy/ScopeCreepGuard/backend/output/pytest-any553-bounded-verified
  --tb=short`: 774 passed in 108.91s. Log:
  backend/.pytest-any553-bounded-verified.log. The lost intermediate terminal
  session supplied no result and is not counted as verification.

## Limits and CI handoff

Baseline alternating-string comparison: 1,024 chars 0.086s; 2,048 chars 0.342s;
4,096 chars 1.386s. The new cap bounds matcher inputs before equality or matching;
normalization remains linear in bounded raw input. Long replies have no novelty
score, with comparison_limit reason and cap 2048 in checkpoint/log/diagnostic data.
Three shared attempts and durable latest-valid fallback remain unchanged for
checked replies. Workflow version v12 fences old stage contracts as before.

An initial broad local run hit Windows permissions reading its pytest-created
temporary directory, including at cleanup; it is not a pass. Rerun with a new
verified workspace-local temporary path and normal elevated test access.
An artificial 32K unbroken-word diagnostic fixture exposed pre-existing slow
language-detection regex work; this change does not fix that separate diagnostic
path. Pure similarity adversarial tests still forbid matching 8K alternating text.

On the previous PR head, frontend/container/rebase checks passed. Backend logs
recorded 904 tests and all static/contract/PDF checks passing through cleanup,
but GitHub still reported the job in_progress. This is not evidence of a failed
rebase or application test. A normal push will create fresh checks. Remaining CI
status belongs to GitHub/reviewer; do not claim green until completion is observed.
Follow-up owner: this task updates PR #34; user/reviewer decides merge. No Linear
status change or merge is authorized here.
