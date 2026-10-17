# PR25: preserve committed generation outcomes on cancellation

Issue: PR25 review discussion4302495537, cancellation during post-commit metrics.
Branch: `codex/profile-behavior-marketing-metrics`; HEAD and fetched remote head
`2714cd6735dd45f3a8d2d56f878c0b838ddeeea8`. PR25 remains open against main.
Continue in this checkout; preserve both unrelated untracked workflow designs.
The user subsequently authorized committing/pushing this correction to PR25. No PR comment, Linear change, worktree or application DB migration.

## Finding and scope

`generate()` catches cancellation from `write()` after its T1 commit while T2
is still awaited. Its failure handler can then append a contradictory terminal
event. Keep cancellation propagation, genuine precommit/provider failure events,
immutable receipts, idempotency and metrics repair. No transaction redesign.

## Steps

- [x] Reproduce with owned disposable PostgreSQL and controlled generators for
  regeneration and translation. Cancel while the successful write's actual
  post-commit callback is blocked. Verify durable revision/receipt/completed
  event and assert no failure, then retry the same key without another provider call.
- [x] Cover cancellation during provider execution and forced precommit failure:
  no successful write/receipt/event, exactly one failure, original error propagates.
- [x] In the existing shielded failure UoW, consult the ownership-checked persisted
  operation receipt before appending `.failed`. Leave a completed command terminal.
- [x] Run affected PostgreSQL workflow/metrics/UoW tests, backend checks and final
  diff review. Reconcile metrics after interrupted T2 and verify no failed count.
- [x] Record exact results and limitations here and in ignored AGENT/WORKLOG.

## Handoff

Owner: publish this authorized correction on the existing PR25 branch; human review/merge separately. Tests use no paid providers and only
disposable infrastructure. Cancellation remains observable to the interrupted
caller; a same-key retry recovers its committed result. No historical event rewrite.


## Reproduction and verification

- RED (required backend working directory):2 postcommit cases failed with contradictory success/failure events;4 provider-cancel/precommit cases passed (19.71s). An initial root-directory invocation was rejected by the migration working-directory guard; no application database was targeted.
- GREEN:6/6 passed (20.38s). Each kind independently verifies committed receipt/revision/event, cancellation propagation, same-key retry without another provider call, and metric read repair with succeeded1/failed0. Provider cancellation and forced failure after tentative save retain failed1/succeeded0 and no committed revision/receipt.
- Broad affected suite:49 passed (88.77s), including both migration-era persistent workflow variants, UoW, profile runtime, metrics late/concurrent repair, domain contracts and architecture boundaries.
- Ruff check and format:pass,354 backend/API files. Final diff reviewed for ownership, receipt hash identity, transaction boundaries and cancellation behavior. Backend transaction and metrics algorithms unchanged.

Commands from `backend/` (root .venv runtime):

```text
../.venv/Scripts/python.exe -m pytest tests/integration/test_generation_cancellation.py -q --require-integration
../.venv/Scripts/python.exe -m pytest tests/integration/test_generation_cancellation.py tests/integration/test_persistent_workflow.py tests/integration/test_marketing_metrics.py tests/integration/test_unit_of_work.py tests/integration/test_profile_activity_runtime.py tests/unit/test_workflow_domain.py tests/unit/test_profile_activity_contracts.py tests/architecture -q --require-integration
```

Commands from repository root:

```text
.venv/Scripts/python.exe -m ruff check backend apps/api
.venv/Scripts/python.exe -m ruff format --check backend apps/api
.venv/Scripts/python.exe -m mypy --platform linux backend/src apps/api/src
.venv/Scripts/python.exe -m mypy --platform win32 backend/src apps/api/src
```

Exact tested files SHA256:

- Workflow: `35990423a07cff39ef7265ad45c608a153e0d287cbc982017c23d8e05df95c21`.
- New tests: `6c13768b98d0bbac08652b6817f8c08851e82732f0b5223e464c463a4fe85d7d`.

No frontend/API contract changes, browser run or paid provider call in this fix.
Existing historical contradictory immutable events, if any, are not rewritten.
Their audit/correction requires a separately reviewed data procedure. This change
prevents future failure events for already committed generation receipts.
- Final: Linux and Windows mypy each passed225 sources; existing untyped-body notes only. Diffcheck passed; no staged files. Owned disposable-container inventory empty. Correction and verification were uncommitted at fix handoff; the subsequent user instruction authorizes their publication. Both unrelated designs remain untouched.
