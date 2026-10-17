# Commercial presentation and execution lanes — implementation record

Scope: F1/F2 from `2026-10-17-nonblocking-full-acceptance.md`.
Plan: [saved before implementation](plans/2026-10-17-commercial-presentation-execution-lanes.md).
Branch `codex/nonblocking-llm-workflow`; base/HEAD
`bc458e28294fa02bf98c17e1ee9de9141899e5e9`, equal to its fetched upstream.
Fetched origin for context only; stayed in the existing checkout. Six existing
untracked documents were retained. No commit, push, PR, Linear write, paid model
call, new worktree, schema change or application database migration.

## Confirmed causes and implementation

**F2:** both `frontend/lib/change-order/document.ts` and Python
`services/documents/service.py` hid the fee for free work but independently appended
the retained rationale. The checkbox and persistence already retained paid values
correctly. This was a presentation-boundary defect, not a generation defect.

`commercialPresentation` and domain `change_orders/presentation.py` now resolve
only designated commercial fields. Free work supplies empty payable amount,
currency and rationale to document preparation. Effort and schedule remain.
The existing TS builder serves preview and Copy; the existing Python preparation
serves PDF. Neither projection writes back to the source. Editor/autosave/API
models, revisions and history remain unchanged. Description, note and special
terms are never searched or rewritten. Shared `ci/contracts/commercial-presentation.json`
fixtures verify paid/free/paid parity in EN/RU/ES with manual, AI and empty rationale.

**F1:** the old production `run()` awaited one `process_one()` before claiming
again. Its SQL priority applied only to the next claim; a held diagnostic consumed
the only operation slot. Retained `scheduling.json` records the user still queued
until release. This record and `free-live.json`/PDF under
`output/e2e/20261017-nonblocking-bc458e2/` were preserved.

The same worker/service now owns two async serial loops: user operations
(`check`, `regenerate`, `translate`, `estimate`, `agreement`) and diagnostics.
Each has exactly one operation slot. `LlmSQLStore.claim(lane=...)` validates the
lane and applies an explicit SQL kind filter with no fallback. Direct test helpers
default to the user lane; diagnostic helpers now select it explicitly.
`FOR UPDATE SKIP LOCKED`, durable claim/epoch/lease/deadline checks and all provider
reservation/accounting paths remain in place. Every store method opens its own
UoW; execution and heartbeat never share an AsyncSession. No new thread, queue
framework or deployed service was introduced.

Each operation owns its execution task and heartbeat. Each lane catches/logs cycle
errors independently and waits on the stop event for two seconds when idle or
after a failed cycle. The worker owns both lane tasks. Signal handling sets one
stop event; both stop claiming and drain under one 30-second deadline. Remaining
work is cancelled together, and cancellation awaits provider accounting,
abandonment and heartbeat cleanup before closing the adapter/database. The bounded
deadline applies to draining; existing cancellation-safe accounting/database cleanup
is awaited afterwards rather than abandoned mid-write. Diagnostic restart reuses
accepted checkpoints and records an interrupted dispatched review as an error
without dispatching that review twice. Diagnostic jobs never publish documents
and remain excluded from user outcome statistics.

## Verification and evidence

All commands below ran in the existing checkout using installed dependencies.
Backend commands ran from `backend/`; frontend commands from `frontend/`.
Evidence is retained under ignored `output/commercial-lanes/`.

- `../.venv/Scripts/python.exe -m pytest tests/unit tests/api tests/architecture -q -p no:cacheprovider --basetemp=../output/commercial-lanes/backend-unit`:
  **651 passed in 64.03s**, before two additional lease/shutdown cases.
  Final rerun is recorded in `backend-unit-final.log`.
- `../.venv/Scripts/python.exe -m pytest tests/unit/test_llm_lanes.py -q -p no:cacheprovider`:
  **4 passed in 0.21s**, covering both-lane shutdown/cancellation and heartbeat
  cleanup, bounded idle waits, lane claim failure isolation, lost diagnostic lease.
- `../.venv/Scripts/python.exe -u -m pytest tests/integration/test_nonblocking_workflow.py tests/integration/test_llm_worker.py tests/integration/test_llm_pipeline.py tests/integration/test_llm_workflow.py tests/integration/test_generation_cancellation.py tests/integration/test_document_workflows.py --require-integration -q -p no:cacheprovider --basetemp=../output/commercial-lanes/pg-regression`:
  **28 passed in 216.14s**. Covers publication, ownership, replay, conflicts,
  immutable snapshots, cancellation/recovery, accounting and historical PDF reads.
- Added free/paid durable persistence scenario, rerun explicitly with
  `tests/integration/test_nonblocking_workflow.py::test_main_agreement_diagnostics_and_concurrency[False-reject]`:
  **1 passed in 30.73s** (`pg-free-persistence.log`).
- Production `apps/worker/main.py` composition tests: **four barrier scenarios
  passed**, including diagnostic accept/reject/provider failure/cancel. Separate
  real-process claim race: **1 passed in 45.75s** (`pg-process-race.log`). Final
  combined confirmation is in `pg-lanes-final.log`.
- Exact successful ordering: **diagnostic blocked → user operation admitted →
  user provider entered → user operation succeeded → diagnostic released**.
  Completed user result/document and main publication stayed unchanged after
  diagnostic rejection/failure/release. Diagnostic max active calls was one.
  Reported controlled calls had token/cost records; cancelled dispatch retained
  `providerOutcomeUnknown` and its positive reservation. Restart did not redispatch
  that review. Structured evidence: `scheduling-after.json`, raw `pg-bounded.log`.
- `node node_modules/vitest/vitest.mjs run --maxWorkers=1`:
  **388 passed / 54 files in 90.57s** (`frontend-single.log`). Focused final editor,
  builder and parity run: **35 passed**, including actual storage remount and Copy
  callback checks (clipboard API mocked in this unit layer).
- `node node_modules/typescript/bin/tsc --noEmit`,
  `node node_modules/eslint/bin/eslint.js .`,
  `node scripts/api-types.mjs --check`: passed; logs `tsc.log`, `eslint.log`, `api-types.log`.
- `../.venv/Scripts/python.exe -m mypy src/scope_guard ../apps/api/src/scope_guard_api`
  and the same command with `--platform win32`: passed, **227 source files**.
  Existing untyped-body notes remain. OpenAPI export `--check` passed.
- Ruff lint/format and `git diff --check`: passed. Existing Vite config and
  next-intl webpack cache warnings remain. No API contract changed.

## Application document evidence and limits

An isolated copy of current frontend sources built successfully with
`node node_modules/next/dist/bin/next build --webpack`. Offline font CSS was used
only in that test copy's process environment. API, existing LLM/export entrypoints,
owned PostgreSQL 17 and private Moto S3 emulator used synthetic data and controlled
provider outputs. No application environment/database or customer data was used.

`api-journey.py` exercised real HTTP through Next: register/login, create project,
check, prepare agreement, paid edits, free selection, supported History archive,
finalize/export, real worker PDF download, reload and paid restoration. It also
verified that later edits did not alter the archived snapshot or downloaded bytes.
`api-journey.json` contains retained source values and PDF SHA256; final log
`api-journey-r3.log` passed. The existing finalization serializer formats 2.5 effort
as 2.50 in PDF; numeric effort and schedule were verified without changing it.

Downloaded `free-application.pdf` has one page. Rendered with
`pdftoppm -scale-to 1400 -png`; **every page (one) visually inspected**. The fee is
No additional charge; effort, schedule/end date remain; dedicated rationale and
payable amount/currency are absent. Text and layout are readable. Inspection record:
`pdf-inspection.json`, image `free-application-page-1.png`.

**Prior-run browser/actual clipboard acceptance was incomplete.** At the user's request
the continuation used the in-app browser entrypoint. It failed twice, including
after reset, with `failed to write kernel assets` / Windows missing path, before
creating a tab. `open_in_codex` queued the local browser panel but supplied no
inspectable surface. HTTP, frontend unit Copy callbacks and PDF evidence do not
claim an actual browser clipboard or checkbox journey. No external browser was
used after the user requested the in-app browser.
The follow-up below closes this gap using an explicitly authorized isolated
external browser after a fresh bounded in-app recovery attempt failed.

Retained failed attempts include pnpm attempting dependency installation (aborted),
sandbox process-spawn/Docker denials followed by authorized successful reruns,
initial synthetic fixture omissions, full frontend memory exhaustion, stalled dev
compilation, and a schema-invalid controlled agreement fixture (extra labels).
These were corrected at the harness boundary; product assertions were not weakened.
The effort-string PDF assertion was corrected to numerical equality to account
for the existing finalization formatting. Original failed logs/PDF were retained.

## Handoff

Changes are intentionally uncommitted. Review the new projection modules/shared
fixture, existing builder integration, SQL claim selection, worker lifecycle and
composition tests. Deployment still uses the existing worker service. Operator
rollout and the blocked in-app-browser/actual clipboard repetition remain with
the project owner. Cleanup and final confirmation results are appended below.

Final confirmation: backend unit/API/architecture **653 passed in 63.63s**;
production scheduler/process suite **5 passed in 52.05s**. Final exact ordering
and accounting are in `pg-lanes-final.log`; earlier failed process fixture is
superseded, not counted as passing. Ruff lint, formatting (300 files) and diff
checks passed after the final edits. Index remains empty; branch/HEAD/upstream
are unchanged, with implementation and documentation left uncommitted.

Cleanup: all recorded synthetic runtime process trees stopped; current runtime
PostgreSQL removed (`database-cleanup.json`). The interrupted broad integration
run left one disposable container, removed only after matching exact immutable
ID/name, creation time and disposable label/password; its remaining generated
database had no application tables (`interrupted-integration-cleanup.json`).
Final Docker listing contains no running `scope-guard.disposable` containers.
Earlier acceptance artifacts and unrelated files were retained. Harness sources,
logs, images and PDFs remain ignored evidence. No application/customer DB was used.

## Follow-up — canonical fixture and completed browser acceptance

This is a new run, separate from the earlier unit and HTTP-only evidence above.
The plan's follow-up was written before changes. Branch/HEAD remain
`codex/nonblocking-llm-workflow` / `bc458e28294fa02bf98c17e1ee9de9141899e5e9`;
origin was fetched for context only, with no checkout/history/publication changes.
The existing uncommitted implementation and unrelated documents were preserved.

### Canonical fixture and focused checks

The sole shared fixture is now `ci/contracts/commercial-presentation.json`.
Python and TypeScript parity tests both read this path. The previous fixture was
moved without changing its bytes; SHA256 before and after is
`73b602fde2ef8c8a9e97863bf6f12208222a4742fb2b1fd62b2ce9501fd92076`.
The root `contracts/` directory contains unrelated pre-existing compatibility
contracts and its README, so it was retained. No API schema changed.

New commands/results:

- From `backend/`: `../.venv/Scripts/python.exe -m pytest tests/unit/test_commercial_presentation.py tests/unit/test_document_service.py -q -p no:cacheprovider --basetemp=../output/playwright/commercial-followup/pytest`:
  **21 passed in 1.37s** (`python-tests.log`).
- From `frontend/`: `node node_modules/vitest/vitest.mjs run lib/change-order/commercial-presentation.test.ts lib/change-order/document.test.ts components/scope-guard/change-order.test.tsx --maxWorkers=1`:
  **35 passed / three files in 5.01s** (`frontend-tests.log`). Installed Next.js
  Vitest guidance was read before changing the frontend test's fixture path.
- Ruff lint and formatting of `backend/tests/unit/test_commercial_presentation.py`
  passed; `git diff --check` passed. Repository source/documentation scan found
  **zero stale fixture references** (`fixture-reference-check.json`). One
  canonical fixture exists, and the old fixture file is absent.
- The entire test suites were not repeated for this follow-up; no product code
  was changed. The existing Vite config warning remained.

### Actual browser run

New evidence directory: `output/playwright/commercial-followup/`.
`cua.rewriteDocumentation` failed with the exact error
`failed to write kernel assets: Системе не удается найти указанный путь. (os error 3)`.
A reset followed by selecting the existing in-app tab failed identically. The
user then explicitly answered **“Yes, use an isolated external browser”** before
an isolated headed Chromium session was created with Playwright CLI. Recovery and
authorization are recorded in `browser-access.json`. No product code was changed
to repair browser automation.

Fresh owned runtime ports were frontend **13374**, API **18374**, private Moto S3
**19374**. The user's existing local application/database and tab on 13274 were
untouched. A fresh disposable PostgreSQL 17 container was migrated only for this
test. API and both existing worker entrypoints ran current uncommitted sources.
The successful prior isolated production frontend build was reused only after
**all 119 frontend product source files matched byte-for-byte**; its build ID and
file hashes are recorded in `frontend-build-provenance.json`. Test-only fixture
path edits do not enter that browser bundle.

`source-before.json` records exact HEAD, Git state and 480 source/contract files.
Post-run comparison found **zero changed source files** (`source-recheck.json`);
the manifest SHA256 is
`869bc7310c51766d21953dc60cd7d0331f5e0a4ab36833a3ca3aba38d3943780`.
The uncommitted changed-file inventory is retained separately.

Through real browser controls, the run:

1. Registered a synthetic account, created a project, obtained its main result,
   and clicked **Prepare agreement**. No API writes substituted for UI actions.
2. Entered effort **2.5**, amount **200 EUR**, rationale
   **“2.5 hours × 80 EUR = 200 EUR.”**, and schedule
   **“3 working days after approval.”** The paid preview and actual autosave
   response contained every intended field (`paid-state.json`, `03-paid-preview.png`).
3. Checked **No additional charge**. The preview displayed free work, omitted
   the dedicated payable terms/rationale, and retained effort/schedule. The real
   autosave response retained amount/currency/rationale (`free-state.json`,
   `04-free-preview.png`).
4. Clicked **Copy**, granted only clipboard permissions, and read the actual
   `navigator.clipboard.readText()` result. `actual-clipboard.txt` contains free
   terms, effort and schedule; dedicated paid fields are absent. No clipboard
   implementation was mocked or replaced.
5. Used **History → Archive current document edits → View archived check →
   Finalize Change Order → Prepare durable PDF → Download saved PDF**. The browser
   download event completed successfully and `download.saveAs` saved the actual
   application PDF (`download.json`, `05-archived-export.png`).
6. Reloaded the actual application. The free checkbox remained checked; saved
   amount/currency/rationale, effort and schedule remained intact. The retained
   rationale and currency were verified in the real editor. Unchecking the box
   restored the complete paid preview and actual clipboard without manual
   re-entry or regeneration (`restored-state.json`, `06-reloaded-free.png`,
   `07-restored-paid.png`). The restored editor equalled its paid source exactly.
7. Verified that both the original automatically archived check and the later
   free-work archive were unchanged. Returned to the archived agreement and
   clicked its existing **Download saved PDF** again; both actual browser
   downloads had identical bytes (`artifact-immutability.json`).

There were exactly **five controlled provider sends**: analysis, replies,
agreement and two diagnostics. The count stayed five across reload, paid
restoration and existing PDF reopening/download; regeneration sends were zero
(`restoration-checks.json`, `controlled-calls.jsonl`). No paid provider calls.

### PDF and cleanup

`free-browser.pdf` was rendered with
`pdftoppm -scale-to 1600 -png output/playwright/commercial-followup/free-browser.pdf output/playwright/commercial-followup/free-browser-page`.
**Every page (one) was visually inspected.** It has no clipping or illegible
layout, shows **No additional charge**, **2.50 hours** (existing finalization
formatting) and the exact schedule. Dedicated payable amount/currency/rationale
are absent. `free-browser.json` records extracted text/page count/hash;
`pdf-visual-inspection.json` records visual review. The second browser download
after paid restoration has the same hash, with no historical artifact rewrite.

Sanitized control actions, screenshots, snapshots, actual clipboard and saved
states are retained. Raw network trace/resources were removed to avoid retaining
cookies/tokens; `browser-actions-sanitized.json` and `sanitization.json` record this.
Optional local Vercel analytics script returned its existing 404; the tested user
journey succeeded. Two stale locator/inline CLI invocation attempts were corrected
from refreshed snapshots/file-based scripts without changing product behavior.

The isolated browser session was closed. All recorded owned runtime process trees
were stopped and the exact disposable PostgreSQL container removed; cleanup
receipts are `cleanup.json` and `database-cleanup.json`. No labelled disposable
containers remained in the final listing. Private export storage was process-local
and stopped with its server. Synthetic test artifacts remain in ignored output.

**Both requested follow-up items are complete.** The in-app tool itself remains
unavailable, but actual browser/clipboard/download/PDF acceptance is now complete
through the user-authorized external browser. Changes remain uncommitted and
unstaged, ready for review; no PR, Linear mutation or application DB migration.

## Authorized PR publication

The user subsequently requested a PR. PR #26 is merged; its original branch HEAD
`bc458e2` has the same tree as fetched `origin/main` at `f4b797a`, with different
commit ancestry. Publication uses `codex/commercial-presentation-execution-lanes`
with a commit parented by that main revision and the exact scoped verified tree.
The current checkout stays on `codex/nonblocking-llm-workflow`; no rebase, merge,
reset or worktree is needed. Six pre-existing untracked documents, ignored local
journals and local evidence are excluded. Prior statements about uncommitted work
and no publication describe their recorded acceptance checkpoints, not this later
explicitly authorized publication. No deployment, application migration or merge.
