# Simplified LLM workflow implementation

Tickets: ANY-543 (client language), ANY-635 (Spanish materials), ANY-553
(regeneration), ANY-554 (usable agreements), ANY-548 (persistence).
Authoritative design: project-draft-ai-workflow.md, priority clarification dated
17 October 2026. This is an implementation record, not Linear acceptance.

Base: fetched origin/main 29c67f4580bea8a7d58530beaeea2abb537af1a9.
Branch: codex/nonblocking-llm-workflow. Existing checkout only. Preserve the four
pre-existing untracked architecture/design documents. No stash/reset, worktree,
commit, push, PR, Linear write, paid provider call or application DB migration.
AGENT.md and WORKLOG.md are ignored local journals.

## Policy difference

The previous acceptance campaign required rejecting language, scope, novelty,
schedule and commercial-content violations and bounded corrective regeneration.
The approved clarification intentionally publishes structurally usable generated
responses despite these findings. Those older rejection expectations must be
updated in tests; passing the new policy does not satisfy conflicting Linear
criteria. Linear descriptions and Mikhail Gushinets's latest comments were read;
no issue state or discussion will be changed.

## Ordered execution

1. Inspect instructions, installed Next.js guidance, current architecture,
   acceptance report/plan and retained exact failure candidates. Reproduce the
   English-note confidence, invalid reviewer path, translated-hours parser and
   pricing/archive failures before product edits. Record actual observations.
2. Separate strict generator JSON/type/required-field contracts from content
   checks. Publish main analysis and three replies transactionally with automatic
   History, without an agreement or semantic acceptance loop. Represent absent
   agreements explicitly; retain original estimate data separately and preserve
   legacy complete snapshots.
3. Reuse llm_operations/llm_steps/provider_calls for a durable diagnostic command
   per completed operation, with a deterministic key and immutable frozen source
   references. Enqueue in the publication transaction; execute on the existing
   worker after the parent is committed. User commands take queue priority.
   Content observations are typed, versioned, field-specific and privacy-safe;
   store normalized codes/values, never prose in technical logging. Diagnostic
   errors are distinct from operation/provider failures. Diagnostics never write
   documents. Reserve an explicit bounded diagnostic allocation from the original
   budget; keep every physical send accounted. A persisted attempted review with
   no recoverable output becomes diagnostic_error after restart, never a duplicate
   model dispatch. Leases, epochs and terminal checkpoints own execution; no
   unowned background task or new worker service.
4. Add explicit idempotent agreement preparation, frozen to the chosen saved
   result/document revision. Reopening existing content makes no provider call.
   Failed generation leaves the response/history intact. Keep CAS/publication
   fencing, ownership, manual amount/currency, editor, free-text schedule and
   Copy/PDF behavior. Translation uses saved edited materials; regeneration keeps
   frozen context/verdict and changes only the selected reply.
5. Limit classification staleness to request/scope/industry; commercial updates
   inform new estimates without invalidating the saved classification solely to
   archive manual terms. Preserve stale handling for actual scope changes.
6. Simplify result UI: verdict/replies/actions; remove reasoning/citations,
   historical context and internal details. RU/EN Prepare agreement, loading and
   error states. Render editor only for an existing/preparing agreement.
7. Meaningful unit/API/disposable PostgreSQL tests, frontend tests, lint/type and
   contract checks; controlled-provider real-browser journey with exact call
   counts. No paid calls. Record failures honestly without weakening assertions.

## Rollout and compatibility

Use a forward migration only if existing operation-kind constraints require it;
apply solely to owned disposable test databases here. Matching API/worker/frontend
rollout required. Version prompts/contracts. Older queued prompt versions fail
safely as version-unavailable; never rewrite frozen inputs or accounting. Completed
old records remain readable. Historical snapshots are not rewritten for UI removal.

## Verification and handoff

Execution record: [implementation and verification report](../2026-10-17-nonblocking-llm-workflow.md).

- [x] Instructions/Git/design/Linear/installed Next.js documentation inspected.
- [x] Saved plan before product edits; four exact/local baseline reproductions retained.
- [x] Main response and automatic History separated from explicit agreement generation.
- [x] Typed durable post-publication diagnostics, bounded accounting and replay isolation.
- [x] Nullable agreement snapshots/API/frontend; old completed snapshots remain readable.
- [x] Historical context, manual terms, CAS/ownership, current pricing and scope freshness.
- [x] Simplified RU/EN result presentation; existing editor/schedule/Copy/PDF preserved.
- [x] Unit/API, affected/full PostgreSQL integrations, frontend/lint/types/contracts/build run.
- [x] First real browser journey completed with actual clipboard/PDF and exact controlled counts.
- [x] Final-code browser repeat: response/agreement/manual edits/Copy/reload passed;
      download wait timed out although SQL export was ready; resume hit host memory exhaustion.
- [ ] Full Docker Compose/S3 checks and final container cleanup: blocked by Docker HTTP 500.
      Owned identities retained in output/nonblocking-workflow/cleanup-required.json.

No application database migration, paid call, commit/push/PR/Linear mutation.
Two failed Docker infrastructure checks are not marked as passes.
Implementation owner: this branch; operator rollout and reconciliation of older
Linear criteria remain with the project owner.

## Separately authorized publication

After implementation verification, the user explicitly instructed “make pr and push”.
Commit the implementation and its new handoff/plan, push the requested branch and
open a PR against main. Preserve/exclude the four pre-existing untracked documents.
Disclose the Docker test/cleanup limits; do not merge or modify Linear.

## PR #26 CI follow-up: saved translation hours

The user supplied the backend CI log and authorized a correction and push to the
existing branch. Base: `c68ae98e1e6e8ee4e232e380bfc814c728fa75ec`;
branch: `codex/nonblocking-llm-workflow`, current checkout, no worktree.

1. Reproduce the five translation failures in the cancellation and persistent
   workflow tests against owned disposable PostgreSQL databases.
2. Correct the editor-to-analysis boundary: convert validated decimal hour text
   into numeric hours only in the detached translation input; omit empty optional
   hours. Retain strict snapshot validation and the saved manual values.
3. Extend integration coverage for edited decimal hours and empty hours, including
   both supported historical schema targets. Keep cancellation, receipt, replay,
   scope freshness and manual amount/currency assertions.
4. Run the full backend suite, lint, formatting, both type-check targets and
   contract freshness checks; record actual results before committing and pushing.

Initial reproduction: **5 failed, 9 passed in 81.33s**, matching the supplied CI
failures. All originate before the translation provider call because saved editor
hours are text while `parse_snapshot` requires a number. The postcommit assertion
and provider-cancellation timeout are downstream effects of that same exception.
No database migration, frontend change, paid provider call or Linear update is
required. Owner: this branch / PR #26.

Final correction also omits absent optional labels instead of injecting `null`.
The first rerun exposed this second invalid input after hours were corrected;
strict snapshot validation remains unchanged.

Verification of the final correction:
- Affected disposable PostgreSQL integration files: **16 passed in 42.91s**.
- Unit/API/architecture: **634 passed**, six Windows temporary-directory setup
  errors; those six tests rerun with owned workspace basetemp: **6 passed in 21.40s**.
- Ruff lint and formatting (358 files), Linux and Windows mypy (226 source files),
  OpenAPI and generated API contract freshness, PDF verification script: passed.
- Initial full-suite attempt loaded the intermediate correction and reported
  733 passed, seven translation failures and eleven Windows temporary-directory
  setup errors. It is superseded for translation by the final 16-test passing run.
- Fresh full integration run with workspace basetemp stalled before completing
  any test; interrupted after several minutes. Full integration success is not
  claimed. Its exact disposable PostgreSQL container was verified and removed.

Evidence: ignored `output/nonblocking-workflow/ci-fix-*.log` and `ci-fix-pdf/`.
No assertions were weakened. Push this scoped correction to the existing PR.
