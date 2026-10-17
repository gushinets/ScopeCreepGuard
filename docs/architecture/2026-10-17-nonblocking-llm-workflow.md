# Nonblocking LLM workflow implementation

Implementation record for ANY-543, ANY-635, ANY-553, ANY-554 and ANY-548.
The [plan](plans/2026-10-17-any-543-635-553-554-548-nonblocking-llm-workflow.md)
was saved before product edits. The priority clarification in
[the approved design](../design/project-draft-ai-workflow.md) governs this work.

## Behavior and ownership

`services/llm/operations.py` freezes owned, versioned commands and budgets.
`worker.py` executes a main check as analysis → three replies → transactional
History/result publication. `changeOrder` is explicitly null; preliminary numeric
estimates have their own snapshot field. No placeholder document is manufactured.
The domain normalizer, serializer, API schema and frontend types accept this state
and still read completed historical records with agreements.

The owner-scoped `POST /api/v2/drafts/{id}/agreement` command is explicit. It uses
the saved analysis, selected material language, saved reply and frozen scope.
If current pricing changed since the check, a new estimate uses those commercial
inputs inside the agreement request, without reclassification or another required
user step. Existing agreements return saved content without regeneration. Main
History and response remain available after agreement errors. Same-key replay and
payload mismatch checking remain; simultaneous same-revision clicks coalesce to
the active agreement command. A newer revision conflicts with in-flight work.

Document publication retains the expected-revision and request fence. Translation
keeps the structured effort/amount/currency and translates saved prose, including
manual edits; older AI estimates are excluded from translation instructions.
Regeneration uses historical scope/verdict and changes only the selected reply.
Estimate merging retains manual amount/currency bindings and free-text schedule.
The optional Update estimate action remains available; reopening never refreshes
automatically. Original analysis/history snapshots are not rewritten.

Classification freshness now compares request, scope and industry. Rate/currency
changes do not invalidate classification solely to archive manual terms. Actual
scope changes still mark the result stale and prevent archive completion.
History reopening obtains the latest saved document for the original analysis
from existing immutable Draft revisions, rather than restoring the initial
agreement-absent snapshot over later edits. No new document table is introduced.

`ResultPanel` removes the separate reasoning/citations/suggestion block, historical
project-condition snapshot and unsolicited verification/diagnostic messages.
Verdict, replies, feedback, language selection and actions remain. RU/EN Prepare
agreement has isolated loading/error state. The existing editor, Copy, durable PDF
workflow and free-text schedule remain. Historical source data is retained.

## Diagnostics lifecycle and accounting

The existing worker owns a second durable `llm_operations(kind=diagnostic)` job.
Its deterministic command key and immutable parent reference are inserted in the
same commit as user publication. It is claimed only after that commit; queued
user operations take precedence. No HTTP-owned or fire-and-forget review task,
new service or generic diagnostic platform is added.

`integrations/llm/stages.py` enforces generator native JSON schemas and bounded
structure correction; it no longer calls content validators/reviewers as output
acceptance gates. Existing language/mixed-language, scope, novelty, commitment,
numeric/unit/currency and schedule checks run from `diagnostics.py` after publication.
Independent field checks prevent one finding from suppressing translation
preservation checks on the same candidate. Semantic review remains bounded and
uses an enumerated field-path schema, the identical prompt list and server check.
`candidate.text` and `candidate.labels.clientEmail` are invalid reviewer paths;
they become diagnostic errors, never generator-repair instructions.

Typed observations contain operation/stage IDs, stage name, field, rule/version,
pass/finding/uncertain/diagnostic_error, optional confidence and normalized language
values, and UTC timestamp. They persist in existing diagnostic step results.
Technical observations never contain candidate prose, requests, documents, PII or
secrets. Review feedback is normalized to server-owned messages. Full generation
checkpoints remain in their existing protected operational storage, not logs.

Diagnostic calls retain provider-call accounting and receive only the parent's
remaining physical-call and monetary allocation, with their own 180-second
deadline. There is at most one semantic review per generated stage (analysis uses
local observations). Transport attempts retain the existing bound. On restart,
accepted decisions and received candidates are reused; a dispatched review with
no recoverable output becomes diagnostic_error without another model dispatch.
Lease/epoch/deadline fences still own every write. Diagnostic code never writes
user documents, so delayed diagnostics cannot replace edits.

Diagnostic jobs are excluded from user-operation outcomes in marketing metrics;
their provider calls still contribute usage/cost accounting. Findings do not set
user-operation failure status or trigger regeneration. Real provider/transport,
missing-output, malformed generator structure and persistence errors remain real
operation failures. Diagnostic outages affect only their separate job/observations.

A complete changed-path manifest is retained in ignored `output/nonblocking-workflow/changed-files.txt`; it excludes the four pre-existing untracked documents.

## Four reproduced defects

Baseline evidence: ignored `output/nonblocking-workflow/before.json`, captured
against unmodified 29c67f4 before product edits. Retained source evidence remains
under `output/e2e/20261017-main-29c67f4/`.

| Case | Before | After / evidence |
| --- | --- | --- |
| Exact English notes | `This change order is a draft and is not legal advice.` rejected at 0.6632; `This document is a draft. It is not legal advice.` at 0.554 | Returned unchanged with one generator call; language findings recorded after publication. Unit and PostgreSQL agreement tests. |
| Reviewer paths | `candidate.text` / `candidate.labels.clientEmail` rejected as nonexistent candidate fields; old runner could fail the user operation | Paths are explicitly excluded by native reviewer schema/prompt/server checks. Each malformed review becomes diagnostic_error. Four PostgreSQL variants include both paths, rejection and outage. |
| Hours translation | `12 additional hours` → `12 horas adicionales` raises commercial binding parser error | Translation is returned unchanged; the parser remains as a diagnostic finding. Structured hours/amount/currency stay server-owned. Exact phrase unit test. |
| Rate then archive | Freshness predicate returned false for identical scope/request after hourlyRate 30→80; retained campaign observed `analysisStale` 409 | Rate-only update preserves classification; manual 175.35 USD archives. Changing scope still sets stale and archive rejects. PostgreSQL test uses real save/update/archive services. |

These are controlled provider and local replay findings, not a new live-model
quality/accuracy evaluation. No paid model calls were made.

## Verification and evidence

Verification completed within the limits below:

- Backend unit/API: 636 passed (56.24s), including malformed generator JSON; fresh workspace-owned temporary directory. Exact output: `output/nonblocking-workflow/backend-final-confirmed.txt`.
- Affected native provider/worker/API/persistence integrations: 22 passed (179s).
- Complete integration suite: 105 passed, 4 failed (342.74s). Rerunning the
  test-only migration-lineage case and both worker variants passed all 3 (the
  worker count now includes the explicit agreement operation). The two remaining
  Docker infrastructure cases failed again; fixture cleanup also errored because
  Docker Desktop returned HTTP 500 to inspection/list requests. A bounded daemon
  health probe then timed out. This is not a claim of a green full integration suite.
- Expanded nonblocking PostgreSQL journeys: 4 passed, including current pricing,
  manual archive, changed-scope rejection, diagnostic isolation/replay and CAS.
- Frontend: 378 tests / 53 files passed with two workers. An earlier unrestricted
  final run exhausted machine memory; its failure log is retained, not counted.
- Linux and Windows mypy: 226 source files passed. Frontend TypeScript, ESLint, API contract freshness, production build, Ruff lint/format (360 files), and diff whitespace checks pass. The final bounded reruns are retained in the evidence root.

Real Chromium evidence is under ignored `output/playwright/nonblocking/` and the
final-code rerun `output/playwright/nonblocking-final/`. The journey registers a
synthetic user, creates a project, checks scope, confirms automatic History and
no agreement call before action, prepares once, edits manual terms, copies actual
clipboard, reloads, archives and downloads an actual worker-produced PDF through
private emulated storage. The single-page PDF was rendered and visually inspected:
2.50 hours, 175.35 USD and 3 working days after approval are readable and unclipped.
The first browser journey completed through download. The final-code repeat
passed response, automatic History, explicit agreement, manual editing, actual
clipboard and reload, then timed out waiting for PDF download. Independent SQL
confirmed the export was already ready with no error and all four operation rows
(main, agreement and their diagnostics) succeeded. A clean-login download-resume
attempt could not start the Playwright driver because the host exhausted memory.
That attempt is retained as an infrastructure failure, not another browser pass.
Provider metadata for each runtime records one analysis, one reply set, one agreement and two
diagnostic reviews. All five calls are controlled native HTTP; zero external sends.
Initial and final attempts have separate evidence directories and counts.

Representative commands (backend cwd unless specified):

```text
../.venv/Scripts/python.exe -m pytest tests/unit tests/api -q -p no:cacheprovider --basetemp=../output/nonblocking-workflow/pytest-unit-confirm
../.venv/Scripts/python.exe -m pytest tests/integration/test_nonblocking_workflow.py --require-integration -q -p no:cacheprovider
../.venv/Scripts/python.exe -m pytest tests/integration --require-integration -q -p no:cacheprovider --basetemp=../output/nonblocking-workflow/pytest-all-integration
../.venv/Scripts/python.exe -m mypy src/scope_guard ../apps/api/src/scope_guard_api
../.venv/Scripts/python.exe -m mypy --platform win32 src/scope_guard ../apps/api/src/scope_guard_api
../.venv/Scripts/python.exe scripts/export_openapi.py --check ../ci/contracts/openapi.json
```

Frontend cwd: `node node_modules/vitest/vitest.mjs run --maxWorkers=2`,
`node node_modules/typescript/bin/tsc --noEmit`,
`node node_modules/eslint/bin/eslint.js .`, `node scripts/api-types.mjs --check`,
`node node_modules/next/dist/bin/next build`.
Repository cwd: `.venv/Scripts/python.exe -m ruff check backend apps/api apps/worker`,
matching `ruff format --check`, `git diff --check`.

Initial failures were retained: system temporary-directory permissions, sandbox
child-process denial, obsolete content-blocking assertions, missing head migration
in legacy integration setup, and the test ledger failing to persist attempted
review state. The fixture now models reservation before dispatch, matching SQL.
Assertions were changed for the approved publication policy, not weakened around
ownership, revisions, provider failures or transactional durability.

## Rollout, compatibility and limits

Forward migration `0007_nonblocking_llm` extends the existing operation-kind
constraint only; no new table or historical rewrite. API/worker startup verifies
the exact compatible catalog. Apply through the guarded operator migration path
after backup and deploy matching API/worker/frontend images; no application DB
migration or deployment was performed here. Only owned disposable PostgreSQL was
migrated. Downgrade is refused to preserve new agreement/diagnostic accounting.

Prompt version is `workflow-v7-nonblocking`; semantic review uses
`semantic_review_v2` and diagnostic contract `diagnostics-v1`. Older queued prompt
versions fail safely before dispatch/reuse. Their immutable inputs/accounting are
not rewritten. Already completed records remain readable. Operators should drain
old work before rollout or disclose version-unavailable operations to owners.

This intentionally reverses older rejection-based ANY-543/635/553/554 acceptance
expectations. A mixed-language, semantic, cosmetic or numerical finding can now be
published. New policy tests do not prove those conflicting old criteria satisfied.
Mikhail Gushinets's latest comments and all five issue descriptions were read;
Linear was not changed. Alignment of business acceptance remains with the owner.
No new live multilingual accuracy campaign was authorized or run.

The existing single-worker/shared queue means an already running diagnostic can
occupy worker time; completed user results remain available independently and
queued user jobs have claim priority. No new worker service is introduced.
History editing continues to use the existing Draft/revision architecture rather
than implementing the broader future check_documents design.

Branch: `codex/nonblocking-llm-workflow`; implementation base is
`29c67f4580bea8a7d58530beaeea2abb537af1a9`. Verification completed before
publication. The user subsequently authorized committing, pushing and opening a PR;
the published commit and PR are recorded in the chat handoff. No merge, Linear write
or application database migration is authorized by that publication instruction.
Four pre-existing untracked design/acceptance documents are excluded from the commit
and preserved locally. AGENT.md and WORKLOG.md remain ignored.

## Cleanup and final limitations

Both local runtime supervisors stopped their five child processes; loopback test
ports 13172/18172/19172 were verified closed. Docker became unavailable during the
last broad verification. Container/volume removal is therefore not confirmed for
the final runtime, repair PostgreSQL fixture and failed disposable Compose stack.
Exact owned identities/provenance are retained in ignored
`output/nonblocking-workflow/cleanup-required.json` and their ownership receipts.
Do not remove any unrelated resources. The private ignored runtime bootstrap is
retained until ownership-checked cleanup can finish. Restarting Docker Desktop
was not attempted because it could interrupt unrelated work. Owner follow-up:
restore Docker health, inspect the recorded labels/IDs, clean only those owned
resources, then rerun Compose startup and conditional S3 restart tests.

The first browser's actual exported one-page PDF remains available and visually
verified. The final repeat's ready PDF was verified in SQL but not downloaded;
this limit is separate from the successful earlier browser/PDF journey. All model
responses were controlled; no live-model multilingual quality claim is made.
