# ANY-641 execution and verification

Plan: [Python services](plans/2026-10-11-any-641-python-services.md).
Base: 75af4114dcff619c020f8a80fb0380aed1ab391b; child codex/any-641-python-services.
Fetched origin main/handover; no parent advancement. Existing checkout, no worktree.

## Execution ledger

- Planning complete/approved; preserved unsaved export and no currency conversion.
- Plan saved and ignored AGENT.md updated; branch created from fetched handover.
- Document/extraction unit RED: 19 missing-service failures; then 19 passed.
- Isolation/API GREEN: 26 passed, including actual child processes and cancellation.
- Disposable PostgreSQL PDF ownership/history tests + isolation: 4 passed in 39.16s.
- Frontend client/editor/form GREEN: 13 passed in 9.52s; TypeScript exit 0.
- Ruff check exit 0; Mypy exit 0, 94 sources at this checkpoint.
- Existing browser visual fixture baseline: 1 passed, 5 PDFs rasterized.

Ruling: retain UI document preparation for local preview/clipboard. Backend services
own export preparation; shared editor models remain in TypeScript for local editing.
Ruling: no rate arithmetic/providers/tests because the approved currency scope has
no conversion caller; numeric interpretation is Decimal and export retains source text.

## Environment-only attempts

- Normal Git switch could not write .git/index.lock; approved escalated switch succeeded.
- uv default cache access denied; approved escalated dependency installation succeeded.
- Default pytest temp root denied; explicit .pytest_cache/any641-* under escalated
  execution succeeded. A giant parametrized test ID was replaced with descriptive IDs.
- Unpinned fallback pnpm tried dependency reconciliation and stopped for no TTY.
  Used installed tool entrypoints; corepack confirms pinned pnpm 10.34.1.
- Sandbox Vite child spawn denied; approved escalated test execution succeeded.
- Existing Vite config-loader warning and Starlette/httpx deprecation remain inherited.

## Final verification

Commands below ran on Windows/Python 3.12 with the locked backend environment.
`.venv/Scripts/python.exe` is the installed equivalent of `uv run python`.
Only owned disposable PostgreSQL containers/databases and temporary files were used.

| Check | Exact command (working directory) | Result |
|---|---|---|
| Complete backend | `.venv/Scripts/python.exe -m pytest --require-integration --basetemp .pytest_cache/any641-final-all -q -p no:cacheprovider --tb=short` (`backend`) | 419 passed, 104.12s; 1 inherited Starlette/httpx warning |
| Additional failure cleanup | `.venv/Scripts/python.exe -m pytest tests/unit/test_technical_operations.py -q --basetemp .pytest_cache/any641-final-cleanup -p no:cacheprovider` (`backend`) | 4 passed, 3.70s; includes one test added after complete run |
| Review regression group | `.venv/Scripts/python.exe -m pytest tests/unit/test_document_service.py tests/unit/test_scope_extraction.py tests/api/test_python_services.py tests/unit/test_http_contracts.py -q --basetemp .pytest_cache/any641-review2 -p no:cacheprovider` (`backend`) | 48 passed, 9.66s |
| Ruff | `.venv/Scripts/python.exe -m ruff check .` and `-m ruff format --check .` (`backend`) | Passed; 173 files formatted |
| Mypy | `.venv/Scripts/python.exe -m mypy src/scope_guard` (`backend`) | Passed, 94 sources; inherited untyped-body notes |
| OpenAPI | `.venv/Scripts/python.exe scripts/export_openapi.py --check ../ci/contracts/openapi.json` (`backend`) | Passed |
| Affected frontend | `corepack pnpm exec vitest run components/scope-guard/project-form.test.tsx components/scope-guard/change-order.test.tsx lib/api/services.test.ts lib/api/forward.test.ts` (`frontend`) | 27 passed across 4 files, 5.83s |
| Complete frontend + contracts | `$env:VITEST_MAX_WORKERS='2'; node ci/scripts/check-gateways.mjs --suite frontend` (root) | 283 passed across 40 files, 31.37s; 20 Python compatibility tests passed, 3.19s |
| Generated frontend contracts | `corepack pnpm api:types:check` (`frontend`) | Passed |
| Types | `corepack pnpm exec next typegen` then `corepack pnpm exec tsc --noEmit` (`frontend`) | Passed; separate type check is required because inherited build skips it |
| Lint | `corepack pnpm lint` (`frontend`) | 0 errors; inherited unused `_s` warning in lib/llm/schema.test.ts |
| Production build | `$env:CIRCLE_NODE_TOTAL='3'; corepack pnpm build` (`frontend`) | Passed; 2 static-generation workers, no source/config change |
| Real production gateway | `.venv/Scripts/python.exe scripts/verify_any641_runtime.py` (`backend`) | 11 checks passed using disposable PostgreSQL |
| Backend image | `docker build -f backend/Dockerfile -t scg-any641-backend-check backend` (root) | Passed; packaged font/JSON assets included in installed wheel |
| Frontend image | `docker build -f frontend/Dockerfile -t scg-any641-frontend-check frontend` (root) | Passed with frozen lock; no migration/database dependency |
| Both images/gateway | `.venv/Scripts/python.exe scripts/verify_any641_runtime.py --containers` (`backend`) | 11 checks passed; actual PDF endpoints and TXT/MD/PDF extraction inside images; owned database/network/container cleanup |
| Compose | `docker compose -f compose.yaml --profile app config --quiet`; same for `docker-compose.yml`; `docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet` (root) | All passed |
| Diff whitespace | `git diff --check` (root) | Passed; inherited CRLF conversion notices only |

The PDF integration test compares drafts, history entries and projects before/after
repeated downloads, forbids generation/proof verification, checks ownership and
private response headers, preserves editable values and handles legacy null snapshots.
Upload tests cover chunked bodies without Content-Length, partial disconnect cleanup,
strict encoding, MIME/extension validation, exact UTF-16 limits, scanned/encrypted/mixed
PDFs and page limits. Process tests cover actual packaged-font rendering, admission,
timeout, cancellation, validation/parser failures, secret exclusion and file cleanup.

## Rendered inspection

Ran `.venv/Scripts/python.exe scripts/verify_any641_pdf.py --output ../output/pdf/any641-reviewed`
from backend, with Poppler available only for verification. Export itself needs no
external renderer or workstation fonts. Inspected all fixture pages as raster images:
EN 1, RU 1, ES 1, German supplied labels 1, long Russian 3, missing commercial values 1,
oversized metadata/amount/approval 6: 14 pages total. Normal/long PDFs remained byte-size
identical after the oversized-cell fix. Confirmed Cyrillic/Spanish accents, dates,
original 2.675 precision, no-charge labels, em-dash missing values, complete ending
markers, approval area and page counts. A high-resolution footer crop confirmed
the footer remains visible on oversized pages. Artifacts stay ignored under output/.

Initial inspection found paragraph keep-with-next leaving excess first-page whitespace;
a failing regression was added, then fixed. Oversized table cells also approached
the footer with ReportLab in-row splitting. Cells now split into bounded paragraph
fragments before table pagination, with a regression for fragment heights.

## Review, failures and scope decisions

One fresh read-only reviewer inspected the full implementation. Its two P2 findings
were fixed and regression tested: nullable draftId now matches OpenAPI, and PDF
text limits apply after normalization. A separate raw PDF-output guard is 2,000,000
UTF-16 units and reports resource exhaustion rather than the normalized-text limit.

The first complete collection hit duplicate API/integration test basenames; renamed
the integration module. Initial full checks exposed stale endpoint/error assertions;
updated endpoint inventory and verified frozen old error codes plus new codes against
both UI catalogs, leaving historical compatibility fixtures immutable. React lint
required isolating scope-edit cancellation from the generic field setter.
The new gateway harness initially signed proofs using real time against an inherited
frozen-clock test server; SCG_AUTH_REALTIME=1 fixes the harness without production changes.

One approval attempt failed because workspace credits were exhausted; no rejected
action ran. Docker Desktop later stalled during an image build. Normal restart stalled;
automatic review rejected a force stop until the user explicitly approved it. Docker
was restarted and both image checks then passed. Concurrent local verification exhausted
Windows memory: one interop test timed out, a later run lost Vite workers, and a local
Next build failed VirtualAlloc. Stopped only the verified owned hung test process;
the final two-worker frontend suite and build passed. No production settings changed.

The pnpm lock removal also prunes already-orphaned Drizzle/esbuild entries inherited
from the Alembic handover; retained dependency versions and manifest entries are unchanged.
No schema migration is added. No rate provider or conversion API exists or is needed;
rate/staleness/provenance failure tests are inapplicable to the approved scope. Decimal
interpretation tests cover rounding boundaries without rounding original display text.

## Handoff and rollback

Matching frontend/backend images roll forward/back together; stored drafts and historical
snapshots require no reversal. Frontend PDF/scope readers, three dependencies and browser
fonts/visual tooling are retired; editing, local preview/clipboard and browser downloads
remain. Unrelated dev.sh, docker-compose.override.yml, pnpm-workspace.yaml and
test_openai.mjs remain untouched and unstaged. Ignored AGENT.md records ownership/progress.

ANY-642 remaining runtime reassessment: measure parser/render admission and memory under
deployment load; reassess single-worker/replica limiter assumptions and proxy topology;
run complete interactive production journeys; choose operational timeout/observability
budgets. OCR, queues, persistent uploads, pricing/rates and deployment remain out of scope.

## CI platform typing correction, 2026-10-11

CI exposed Windows-only attributes that the initial Windows-host Mypy run could see
but Linux typeshed could not. Reproduced both errors with
`.venv/Scripts/python.exe -m mypy --platform linux src/scope_guard` before the fix.
Technical operations now select Windows creation flags in a `sys.platform` branch;
Windows Job Object access has an explicit platform guard. No type ignores or
runtime fallback were added. CI also checks `mypy --platform win32 src/scope_guard`.

Verification: Mypy passes for both Linux and Windows targets, 94 sources each.
The exact CI command `uv run mypy src/scope_guard` also passed inside a disposable
`python:3.12-slim` Linux container with locked development dependencies and a
read-only backend mount copied into container-local storage. Existing untyped-body
notes remain. Ruff check/format pass for technical infrastructure; process-isolation
tests pass (4 tests, 4.24s). No database was used for this correction.
