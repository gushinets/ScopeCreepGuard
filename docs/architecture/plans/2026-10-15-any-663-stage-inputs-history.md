# ANY-663: stage inputs and unapplied History fixes

**Scope:** Two P2 findings in PR #23. Continue the existing branch/check-out from
84a5244; preserve .gitignore, local designs and ignored logs. No application DB
migrations or paid model calls. Existing authorization covers committing/pushing
these corrections to the same PR.

1. Add failing regressions through the native runner for regeneration/estimate
   with an unrelated near-1MB Draft field. Project each stage's frozen inputs
   explicitly: common project/request/language, accepted analysis without old
   replies/labels, selected saved reply for regeneration, commercial/work context
   for estimate, only relevant saved materials for translation. Keep full frozen
   inputs for local validation/persistence and preserve the 32,768-byte gateway
   limit. Verify relevant oversized inputs still fail. Bump persisted request
   prompt version to workflow-v3, rejecting older pending checkpoints explicitly.
2. Add delayed-analysis frontend regressions with applied=false/draft=null and
   historyEntryId. Refresh project History independently of Draft application,
   while preserving newer text, edit/revision and navigation guards. Do not select
   the old History result over the current Draft; guard the asynchronous refresh.
3. Run focused runner/language/gateway and persistent-store/navigation/frontend
   regressions, Ruff/format/Mypy/TypeScript/lint. Keep controlled tests distinct
   from live tests. Record actual results and any Docker limitation; commit only
   these changes, push to PR23 and update its description. No Linear changes.

**Compatibility:** No public API or database schema changes. The existing
workflow_v2.py compositor gets a v3 input projection revision; old completed
results remain readable, but pending v1/v2 work must not silently resume under
new serialized requests. Do not reset counters or rewrite old checkpoints.

**Evidence:** Both failures reproduced before fixes: backend 2 failed/1 passed; frontend 1 failed/21 passed. After fixes, the focused native runner/language/gateway suite passed 58 tests in 85.90 s; the affected frontend persistence/navigation/operation suite passed 46 tests in 13.13 s. Ruff and format passed (310 files), normal and Windows Mypy passed (198 source files), and frontend TypeScript/affected ESLint checks passed. Fresh read-only review found no further issues. Docker Linux daemon was unavailable, so no local PostgreSQL tests ran in this pass. Earlier head 84a5244 passed all CI jobs in run 38725817654; this does not verify these subsequent changes. No live provider calls or runtime latency/cost measurements. No migrations or application database changes. Machine duration for the complete task was not measured; human/billable effort is unknown.
Installed Next.js use-client guide read before editing the provider component.
