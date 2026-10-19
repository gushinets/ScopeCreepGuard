# ANY-553 — regeneration textual similarity

- Base: 50ab0b6 (ANY-549 plus structured translation preservation); fetched origin/main 837bb5f has the same tree. Preserve current ancestry.
- Branch: codex/any-553-reply-similarity, existing checkout. Initial tree clean, including domain/drafts/workflow.py.
- Scope: deterministic normalized text similarity for regenerate/reply only; shared three-attempt PydanticAI budget and nonblocking durable fallback. No frontend/API, service, reviewer or publication changes.
- Workflow: implement directly as authorized; no worktree/reset/stash/commit/push/PR/Linear mutations. AGENT.md and WORKLOG.md remain ignored.

## Steps
1. Add focused failing tests for normalization, boundary, retries and restart recovery.
2. Add pure NFKC/casefold/punctuation/whitespace SequenceMatcher function with named 0.72 threshold. Bound comparisons using existing 32768-byte provider input ceiling and explicit reply output limit; never truncate text for comparison.
3. Reuse llm_steps.feedback JSON for a private novelty checkpoint (valid candidate, score, attempt, exhausted). Preserve it when retry feedback changes; keep accepted_result reserved for acceptance. Validate cached candidates identically and recover the persisted budget.
4. Add narrow output validator and exhaustion fallback; retain provider/infrastructure failures. Reuse similarity in publication diagnostics and record numeric metadata without logging prose.
5. Exercise controlled provider unit/SQL integration and recovery tests using owned disposable PostgreSQL; run Ruff/mypy, inspect diff and update local journals.

## Verification and handoff
Implemented. Verification evidence and limitations follow below. Follow-up owner: user/reviewer for review and any separately authorized publication.

## Implementation record

Implemented directly on the authorized branch, leaving index empty and all changes
uncommitted. No new persistence field/table: feedback JSON already stores private
stage-validation state and can preserve a namespaced novelty checkpoint across
reserve(candidate=NULL). Ordinary retry feedback is merged, not substituted.
The checkpoint contains the latest typed valid candidate, score, threshold and
candidate attempt. On output retry exhaustion it is marked exhausted and accepted
through the unchanged worker flow; acceptance drops its duplicate candidate text
and retains numeric metadata. accepted_result remains unset until actual acceptance.
The provider row supplying the fallback is marked accepted, even if a later row
contains malformed JSON. Provider/budget/infrastructure failures are not caught as
novelty exhaustion. Failure lookup ignores metadata-only feedback without a rule.

Comparison uses the original frozen selected saved text (manual edits included),
with the existing generated-tone fallback. Native and cached output take the same
check, using the persisted semantic/transport counters. Output structure and novelty
share three generation attempts. Empty normalized reference skips the comparison;
empty output still fails its native schema. No broad semantic validation restored.

Bound: 32768 raw/normalized characters; existing gateway input remains capped at
32768 UTF-8 bytes including schema/framing, and provider output at4096 tokens.
No truncation or approximate score. SequenceMatcher has quadratic worst cases;
comparison and postpublication local diagnostics run in the existing thread pool
so heartbeat/cancellation remain responsive. A cancelled comparison may still use
CPU until completion, but has no persistence/publication capability.
Workflow version v11 fences old v10 in-flight contracts without changing frozen input.

### Files and purpose

- backend/src/scope_guard/domain/llm/reply_similarity.py — pure normalization, inclusive0.72 threshold, exact ratio, size guard, frozen selected-reply extraction.
- backend/src/scope_guard/domain/llm/runtime.py — v11 workflow compatibility fence.
- backend/src/scope_guard/integrations/llm/stages.py — PydanticAI novelty validation, durable checkpoint, cached validation and narrow nonblocking exhaustion fallback.
- backend/src/scope_guard/database/repositories/llm.py — merge durable private state; retain numeric acceptance metadata, accept correct call, handle metadata-only failure feedback.
- backend/src/scope_guard/integrations/llm/diagnostics.py — shared scoring and numeric similarity observations after publication; offload CPU checks.
- backend/tests/unit/test_reply_similarity.py — normalization, inclusive boundary, retry budget, source anchoring, malformed/no-valid output, operation isolation, logs and heartbeat.
- backend/tests/integration/test_reply_similarity_recovery.py — nine controlled PostgreSQL cases for durable recovery/publication, cached candidates, acceptance/provider failures and revision conflicts.
- backend/tests/fixtures/llm_ledger.py — private checkpoint support in controlled unit ledger.
- backend/tests/unit/test_llm_review_corrections.py — replace obsolete one-call duplicate expectations with retries/nonblocking fallback.
- backend/tests/unit/test_any688_validation.py — shared similarity diagnostic rule identifier.
- backend/tests/unit/test_any688_semantic_review.py — below-threshold candidates isolate existing diagnostic-review tests from novelty retries.
- backend/tests/integration/test_llm_pipeline.py — distinct multilingual formulations and expected1/2/3attempt counts.
- backend/tests/integration/test_llm_execution_lanes.py — distinct reply fixture keeps lane-independence test focused on one accepted formulation.
- This plan — execution, evidence and handoff. Local AGENT.md/WORKLOG.md updated and ignored.

### Verification evidence

Run from backend with ../.venv/Scripts/python.exe unless noted:

- `-m pytest tests/unit/test_reply_similarity.py tests/unit/test_llm_review_corrections.py tests/unit/test_any688_semantic_review.py tests/unit/test_translation_commercial_terms.py -q -p no:cacheprovider --tb=short` —153passed17.39s, including28new tests.
- `-m pytest tests/integration/test_reply_similarity_recovery.py tests/integration/test_llm_pipeline.py tests/integration/test_nonblocking_workflow.py tests/integration/test_llm_worker.py tests/integration/test_translation_commercial_workflow.py --require-integration -q -p no:cacheprovider --tb=short` —38passed330.85s. Log backend/.pytest-any553-focused-integration.log.
- `-m pytest tests/integration/test_reply_similarity_recovery.py --require-integration -q -p no:cacheprovider --tb=short` —9passed80.62s after acceptance cleanup. The strengthened final fixture, including a distinct third candidate to prove latest-valid fallback, passed all9cases in88.00s. Logs backend/.pytest-any553-recovery-final.log and backend/.pytest-any553-recovery-final-2.log.
- From repository root: `.venv/Scripts/python.exe -m ruff check backend apps/api`, `-m ruff format --check backend apps/api` —pass,370files formatted.
- `-m mypy backend/src/scope_guard apps/api/src/scope_guard_api` and `--platform win32` —pass,229sources; existing untyped-function notes only.
- `.venv/Scripts/python.exe backend/scripts/export_openapi.py --check ci/contracts/openapi.json` —exit0, no public schema change.
- `git diff --check` —pass; domain/drafts/workflow.py diff empty; journals ignored.
- Independent read-only code review completed; two P2 findings fixed and regression-tested (CPU heartbeat starvation and failure feedback without rule). No remaining major finding.
- Final lane verification: `-m pytest tests/integration/test_llm_execution_lanes.py --require-integration -q -p no:cacheprovider --tb=short` —5passed73.32s, including actual competing worker processes. Log backend/.pytest-any553-lanes-final.log.
- All unit/API/architecture checks: `-m pytest tests/unit tests/api tests/architecture -q -p no:cacheprovider --tb=short --basetemp D:/Devpy/ScopeCreepGuard/backend/output/pytest-any553-unit-final` —763passed74.28s. A verified new workspace-local temporary directory avoids the locked host pytest temporary directory. Log backend/.pytest-any553-unit-final.log.
- The isolated migration test `tests/integration/test_alembic_baseline.py::test_guarded_migrate_upgrades_known_baseline_to_test_only_future_head` with a verified new workspace-local `--basetemp` passed6.22s. Log backend/.pytest-any553-broad-recheck.log.

### Full-suite limitation (not a full-suite PASS)

`-m pytest --require-integration -q -p no:cacheprovider --tb=short` was attempted.
The run was interrupted after roughly11minutes, including7minutes without visible
progress beyond15%. Its last flushed progress contains four setup errors:

- test_alembic_baseline.py::test_guarded_migrate_upgrades_known_baseline_to_test_only_future_head
- test_compose_startup.py::test_profile_free_stack_migration_restart_replicas_and_failure
- test_entrypoint_signals.py::test_entrypoint_terminates_migration_child_without_starting_server[TERM-143]
- test_entrypoint_signals.py::test_entrypoint_terminates_migration_child_without_starting_server[INT-130]

These tests use the shared tmp_path fixture. The first was reproduced independently
as WinError5 reading C:/Users/jackd/AppData/Local/Temp/pytest-of-jackd; it passes with
workspace-local --basetemp. Also recorded four failures in
test_llm_execution_lanes.py::test_production_main_keeps_user_lane_available for
accept/reject/failure/cancel: its duplicate-output fixture still expected one call.
That fixture was corrected to a below-threshold formulation and all5lane tests pass.
The interrupted full-run log has no final summary. Its owned PostgreSQL container
was identified by name/image/disposable label and removed; its Python process stopped.
No application container, database or volume was touched. No broad integration
PASS is claimed; remaining full-suite/Compose/signal verification belongs in CI
or a separately bounded run with writable temporary storage.

No paid provider calls or application-database mutation. PostgreSQL fixtures own
random disposable databases/containers. No commit, push, PR or Linear mutation.
Follow-up owner: user/reviewer for review and separately authorized integration;
requested implementation and focused verification are complete; broad integration
verification remains limited as documented above.

## Publication authorization

The user subsequently authorized creating a PR, including the necessary commit
and push. Initial publication merged origin/main (837bb5f); CI rejected that
merge commit. The linear-history correction below supersedes that approach.
Fresh prepublication checks: 28 similarity unit tests passed in7.22s, Ruff lint
and formatting passed (370files), and git diff --check passed. Earlier broader
verification and the full-suite limitation above remain explicitly recorded.
Local AGENT.md and WORKLOG.md stay ignored; Linear status changes remain outside scope.

## CI history correction

The user requested fixing the failed require-rebase job. The script requires
current main as an ancestor and no merge commits in origin/main..HEAD. The
publication merge satisfied only the first condition.

Preserved the original reviewed tip4e1a59d on the local backup branch
codex/any-553-before-ci-rebase. Replayed only the ANY-553 feature commit onto
origin/main837bb5f, dropping the three inherited ANY-549 commits already integrated
there. Before this documentation correction, the rebased tree matched4e1a59d
exactly. Product code and tests remain unchanged; the correction changes history
and this implementation record. Update PR34 with an exact lease against its
previous remote tip so another person's push cannot be overwritten.
