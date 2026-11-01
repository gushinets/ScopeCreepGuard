# ANY-764 Optional internal diagnostic review — implementation plan

> Execution handoff: use Superpowers executing-plans and test-driven-development. This document is the approved design and implementation record; the user's detailed ANY-764 instructions and the 2026-11-01 Linear clarification are authoritative.

## Goal and baseline

Optional internal semantic review of generated output, disabled by default.
Base: `355c1da425aacaa6e617aff98f394e5958012b67` (`origin/main`).
Branch: `codex/any-764-optional-diagnostic-review`; ordinary branch in the existing checkout, no worktree or clone. Preserve both untracked acceptance reports, existing stashes and private files. Do not commit WORKLOG.

Inspected description/comments of ANY-764 and traced publish → enqueue_diagnostics → diagnostic lane → execute_diagnostics. Current diagnostics are local only; SemanticReviewer has no production caller. Scheduling already creates unused review slots and freezes remaining primary budget. SQL operation/step statuses are constrained; JSON results can represent review outcomes without a migration.

## Constraints and design

- Only internal diagnostic review changes. No primary prompts, validation, retries, selected model, UI, permissions, Draft, History, commercial terms or email behavior changes. The llm-worker retains both lanes. No new service, broker or database.
- Settings flag `SCOPE_GUARD_LLM_SEMANTIC_REVIEW_ENABLED=false`; missing means false. Pass it only through actual worker scheduling, diagnostic execution and diagnostic dispatch protection.
- Freeze opt-in, independent reviewer prompt/schema versions and source step/output provenance when scheduling diagnostics; do not alter primary policy. Keep source operation/stage IDs, evaluated-output hash and source versions traceable.
- Always schedule local observations. Only opt-in schedules review stages for replies, reply, change_order and estimate; analysis remains local. Isolate diagnostic insertion in a savepoint so bookkeeping failure cannot roll back publication.
- Dispatch requires frozen opt-in AND runtime true on every physical attempt, including transport retries. Runtime configuration is process-local, not hot-reloaded.
- Use frozen parent input and accepted stage output, never current Draft. Findings remain observations, with no correction, republication, primary failure or recursive review.
- Independent reviewer versions must agree at scheduling and execution. Keep local diagnostics compatible with diagnostics-v1; missing old opt-in disables review regardless of runtime true.
- Distinguish completed_clean, completed_findings, skipped_disabled, skipped_budget, unavailable_version and failed (including unknown outcome) in existing JSON results. Unsupported analysis is explicit. Never call skipped/failed review passed.
- A diagnostic-only fenced writer records local work and terminal outcomes without a paid-budget prerequisite. Preserve review decision cache compatibility. Do not mark malformed output accepted in provider accounting.
- Reuse accepted decisions and received candidates before considering dispatch. Never redispatch accepted stages or unknown dispatched reviews after restart. Preserve epoch/lease/deadline checks; cancellation and lease loss propagate.
- Existing expired jobs retain historical failed status; no deadline extension or backfill. Preserve accepted historical reviews and all provider costs.
- Reuse remaining diagnostic maxCost/maxCalls, rate bounds, model and ProviderGateway's maximum two transport attempts. One semantic review per supported stage. No new allowance or reviewer-model selection.
- Existing provider_calls retain requested/actual model, call IDs, usage and costs. A real cost-bound overrun retains the ledger's failure and error/call linkage; do not force success.

## Ordered implementation

- [x] 1. Add failing enabled/disabled, persistence and recovery tests. Extend existing PostgreSQL workflow fixtures and controlled provider boundary; no real provider calls.
- [x] 2. Add Settings/worker wiring, frozen diagnostic configuration, supported-stage scheduling, savepoint isolation and per-attempt SQL dispatch guard. Main files: core/config.py, services/llm/worker.py, database/repositories/llm.py, apps/worker/main.py.
- [x] 3. Add optional reviewer orchestration, independent versions, diagnostic result persistence and recovery. Main files: integrations/llm/diagnostics.py, semantic_review.py, stages.py and domain/llm/runtime.py. Keep primary behavior unchanged.
- [x] 4. Update root/backend .env.example, worker Compose definition (production inherits), worker/main README and existing workflow design. Explain activation, recreation, budget, old jobs and provenance.
- [x] 5. Run scoped and full backend regressions, lint/type/contract checks and synthetic Compose configuration matrix. Exercise production worker composition with controlled provider and real PostgreSQL, then isolated documented worker component with migration gate and test-only adapter injection/no external provider transport. Record images versus overlays separately. The unrelated S3 build limitation below remains explicit; a green complete suite is not claimed.
- [x] 6. Fresh whole-branch review, fix material findings, scoped commit/push, PR to main and verify actual head/base. Do not merge or update Linear.

## Acceptance and verification

Default/missing/false produce zero review calls and retain local observations; true reviews only supported stages. Historical missing configuration remains disabled, runtime false suppresses opted-in jobs and retries, and enabling does not backfill. Persist findings without modifying source result/Draft/History/user edits. Distinguish every outcome. Verify budget preflight, bounded failures, accepted/candidate replay, unknown recovery, lost lease, nonrecursion, version/model attribution and physical-call costs. Test enqueue failure after partial insertion and cost-bound overrun. Primary generation, validation and required retries must regress unchanged.

Use real disposable PostgreSQL and synthetic env fixtures, unique Compose project names and documented component entry points. No database resets, volume deletion, prune or stopping unrelated services. Record tested revision/local changes, image IDs/revision labels, actual topology, commands and results. Component evidence does not establish full application readiness.

## Deployment, limitations and ownership

Build new worker image; stop/drain all old llm-worker binaries for this deployment; follow documented maintenance and one-shot migration gate; recreate worker with flag false initially. An old binary is not controlled by the new flag. Already submitted requests can finish and incur cost. Enabling later affects only newly frozen opt-in jobs. Changing .env requires container recreation.

Implementer owns completion and evidence below; maintainers review/merge the main-targeted PR. No quality guarantee, evaluation dataset, dashboard or user profiling is introduced.

## Implementation evidence

- Plan saved before application code changes. Initial Git state: only the two user-named untracked reports; existing stash preserved.
- RED: initial 9 optional-review unit cases failed on missing Settings/runner support. GREEN: 47 diagnostic/reviewer/nonblocking unit tests passed; first 12 SQL cases passed, then 15 with recovery/dispatch cases.
- Fresh independent review found unknown dispatch + runtime-false misclassification and noncanonical first-run findings. Both received failing reproductions, then fixes. Combined optional-review unit/SQL run: 26 passed; supported-material stage additions: all 12 optional unit cases passed. Unknown dispatched work remains failed/diagnosticOutcomeUnknown even when disabled. Canonical findings are identical on accepted replay.
- Ruling: retain native decision/violations in successful review-step accepted_result; canonical normalized findings and provenance belong in diagnostic operation JSON. This preserves the existing reviewer recovery contract without a schema migration. Terminal skipped/error step results carry explicit outcomes, not a synthetic review decision.
- Primary regression fixture corrections: publication rollback injection forwards the new diagnostic keyword; a translation test that repurposes a review-slot explicitly assigns primary prompt/schema versions. Production primary validation/retries were not weakened. Existing lane/pipeline/nonblocking PostgreSQL suite: 12 passed.
- Ruff check and format check passed (433 files); both documented mypy invocations passed (248 source files each); OpenAPI contract check passed. CI helper tests: 14 passed after rerunning with access to their own temporary directories.
- Compose configuration matrix passed on 5.6.0 and official 2.24.0, including default false, true/false worker component/full entrypoints, production inheritance, root/deploy parity and synthetic-secret isolation. Compose 2.24 uses documented explicit deploy env-file fallback.
- Fresh worker image `scope-guard-worker:any764-test`: `sha256:c390dad273d63aa43a1cc08c5712b57412ad570662b60884dc41ff694ccaaf69`; revision label `355c1da425aacaa6e617aff98f394e5958012b67`. Built with `docker build --target export-worker --build-arg SOURCE_REVISION=355c1da425aacaa6e617aff98f394e5958012b67 -f apps/api/Dockerfile -t scope-guard-worker:any764-test .` from base plus this branch's then-uncommitted diagnostic implementation. No source overlay. The PR diff records local modifications relative to that base.
- Component command: `uv run --no-sync python scripts/verify_optional_review.py` from backend. Actual topology: maintained `deploy/compose.llm-worker.yaml`, postgres + one-shot migrate + one-off llm-worker using the same fresh runtime image. Test-only mounted adapter/stop-observer fixture invokes installed production `/app/export_worker.py`; socket audit guard permits only that PostgreSQL endpoint. False produced analysis_v1/replies_v1 only; true added exactly one semantic_review_v2 and completed_clean. No paid provider calls. Project `scg-any764-test-fac83be7fad043a582a694aa0e235eba`; only its containers/network cleaned up, named volume retained. Initial smoke fixture omitted a required profile; fixed fixture, repeated successfully.
- Full backend command: `uv run --no-sync pytest -p no:cacheprovider --require-integration -q`. Initial run encountered Windows access errors in shared pytest TEMP and exposed the two fixture compatibility issues above; it was superseded and stopped. Repeat with `--basetemp ../.cache/any764-full-final --tb=short -v`: **1111 passed, 9 failed** in 942.78 seconds. Two failures used the already-loaded old translation fixture; six subprocess/technical tests lost the editable package when an attempted dependency update hit a Windows-locked Pillow binary. Updating dependencies while that run was active was premature. After it finished, `uv sync --locked --all-packages --all-groups --python 3.12` succeeded; targeted repeat of every failed file produced **52 passed, 1 failed**. The eight non-S3 failures are resolved; the S3 limitation is below. Separate complete unit/API/architecture recheck: **941 passed** in 109.97 seconds.
- Evidence logs are private local `.cache/any764-*.log`, excluded from commits. Component evidence is bounded; no full-application readiness claim, external delivery or real-model correctness claim.

### Final merged state and delivery (2026-11-02)

- While verification ran, main advanced to `fb4d596154809d653291fef2f52a64873707fc02` (SMTP deployment checks and dependency fixes). The unpublished scoped commit was rebased without merge commits. The only conflict was the Compose verification script; both upstream SMTP assertions and ANY-764 flag assertions were retained. No email implementation changes enter this PR diff.
- Tested implementation commit: `6591c3a28ce1251da020e2b7c4dcd244722ea6a3`. Fresh worker image: `sha256:efeaa1c9a47aa7a7b0e42df161a7c64cae80a61d18a375e318f3fe41fe71f57e`, revision label exactly that commit. Same build command as above with SOURCE_REVISION=6591c3a28ce1251da020e2b7c4dcd244722ea6a3. Build used the updated main lockfile; no source overlay.
- Repeated component smoke on that image passed false/true with the same exact 2 / 3 controlled physical-call counts and PostgreSQL-only socket guard. Project: `scg-any764-test-61bfc2d8a01d42089170e1f45c7700b7`; its postgres volume is retained. Both Compose matrices passed again on the merged state, including the new upstream SMTP checks.
- Final Ruff check, format check (433 files), both mypy commands (248 source files each), and OpenAPI freshness check passed after dependency restoration. No paid LLM calls were used.
- Remaining limitation: unchanged `test_conditional_s3_upload_and_storage_restart` cannot build its MinIO fixture in this Docker environment. The existing Go cache contains empty sources (`expected package, found EOF`). A separate builder/cache `scg-any764-6591c3a`, without selecting it globally or pruning anything, failed before application execution with `/bin/sh: exec format error` in golang:1.24.2. The builder was removed with `--keep-state`, preserving its cache volume. The S3 test remains unverified; neither a fully green suite nor full application readiness is claimed. Follow-up belongs to the Docker/build-environment maintainer; no storage or fixture implementation was changed in this diagnostic-only task.
- Published ordinary branch: `codex/any-764-optional-diagnostic-review`. PR: https://github.com/gushinets/ScopeCreepGuard/pull/57, base `main` (`fb4d596154809d653291fef2f52a64873707fc02`), initial head `6591c3a28ce1251da020e2b7c4dcd244722ea6a3`, verified from the create response. Subsequent evidence-only commit leaves tested application code unchanged. PR remains unmerged; Linear statuses/comments were not modified.
- Both user-named untracked reports and the existing stash remain outside commits. No worktree/clone, force-push, published-history rewrite, database reset, volume deletion, or Docker prune was performed.
