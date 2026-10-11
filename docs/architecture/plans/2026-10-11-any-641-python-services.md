# ANY-641 — Python document export and scope extraction

Approved in chat on 2026-10-11. Issue: ANY-641, under ANY-637; dependencies
ANY-638/639/640, inheriting the completed ANY-642 Alembic handover.

## Checkout and delivery

Parent: `origin/codex/any-642-alembic-handover` at
`75af4114dcff619c020f8a80fb0380aed1ab391b`, including `4359f23` future-revision
support and subsequent catalog guards. Child: `codex/any-641-python-services`.
Chain: ANY-638 -> ANY-639 -> ANY-640 -> ANY-642 handover -> ANY-641.
Fetch origin main and handover; inspect any newer parent before branching.
Use this checkout, no worktree; never modify/merge/rebase/force-push main.
Preserve unrelated dev.sh, docker-compose.override.yml, pnpm-workspace.yaml and
test_openai.mjs unchanged/unstaged. Update ignored AGENT.md, never add it to Git.
Commit only explicit ANY-641 paths with a conventional message and push the child.

## Boundaries

Frontend: forms, editing state, preview presentation, clipboard/download interactions,
localized UI and API client. Next routes: one-call forwarding only, no business fallback.
FastAPI: authentication dependencies, parsing, HTTP errors and file responses.
Use cases: ownership, immutable context, read transaction closure and orchestration.
Concrete services: validated explicit input/detached output, no cookies/current-user
lookup or writes. Infrastructure: renderer, packaged fonts, readers, temporary resources,
local process isolation. Repositories: persistence only. No writes in new operations.

## Contracts

### GET /api/drafts/{draftId}/pdf

Register before the catch-all draft route. Authenticate then load only the owned
saved draft. Render saved editable Change Order and historical context. Return
application/pdf, attachment `change-order-{draftId}.pdf`, private/no-store.
401 errors.authRequired; malformed/missing/foreign IDs: 404 errors.draftNotFound.
400 for absent Change Order, missing language labels, unsupported language/glyphs;
sanitized 500 for render failure. Private caching also applies to errors/gateway outages.
No LLM, proof verification, estimation, draft/history/project writes or current-term lookup.

### POST /api/change-orders/pdf

Preserve unsaved export (explicit user selection). JSON: projectId UUID, optional
draftId UUID, changeOrder existing EditableChangeOrder shape. Authenticate/check
owned project; if draftId exists check owned matching draft and use its historical
context. Otherwise render submitted editable values without current commercial
terms. Reuse editor/label validation; 1,000,000-byte body cap. No proof or writes.
Same PDF/error contract; filename derived from validated identifier.
Frontend uses GET for saved unchanged data and POST for unsaved/changed values;
never implicitly save before export.

### POST /api/scope/extract

Authenticated multipart, exactly one file; response `{text, warnings}`. Warnings
are discriminated objects: pages_without_text with pageNumbers, nul_removed.
No source contents/exception messages in warnings/logs. Does not save projects.

- 5 MiB file, multipart body 5 MiB + 64 KiB overhead, streaming enforcement even
  without Content-Length. TXT/MD/PDF case-insensitive extensions.
- TXT MIME text/plain; MD text/plain, text/markdown, text/x-markdown; PDF application/pdf.
  Empty/octet-stream accepted only with matching extension/content validation.
  Reject mismatches, multiple files and unsupported extensions.
- Strict UTF-8, BOM accepted/removed, normalize line endings, remove NUL with warning,
  trim edges. Invalid encoding is explicit failure.
- 100,000 UTF-16 code units extracted text, reject rather than truncate; 200 PDF pages.
- Reject encrypted PDF without password recovery; explicit corrupt/unreadable/empty
  errors. Image-only PDF reports no extractable text/OCR unavailable. Mixed PDF
  returns text plus pages_without_text warnings.
- Status: 400 malformed/unreadable; 401 auth; 413 file/body/text/page limits;
  415 unsupported; 422 no extractable text; 504 timeout; sanitized 500 unexpected.
  Existing `{error: "errors.…"}` envelope.

## Services, packaging and frontend changes

Add services/documents preparation/localization and services/scope_extraction
models/service, plus infrastructure document renderer/assets and format-specific readers.
Reuse draft values/language/label validators, no duplicate draft domain model.
Preserve saved edits: descriptions, amounts, currency, hours, conditions, parties,
approval fields, date and no-charge behavior; never reconstruct from AI proposals.
Legacy missing/null snapshots stay unknown; use saved document details, no current
project commercial terms. Missing commercial fields display em dash with their
localized labels, never zero or silent omission.

EN/RU/ES built-ins and existing label-driven language list; Babel date formatting
with UTC date-only semantics, EN/RU/ES/German fixture parity. A4, navy/amber header,
metadata panel, numbered sections, commercial rows, approval and page footer.
Pagination must split oversized metadata/commercial rows and approval text without
clipping/truncating values. Explicit glyph checks. ReportLab with embedded Noto Sans:
move fonts/OFL into backend package, reproducibly instantiate static regular from
existing variable font (development script); retain static bold. No runtime external
renderer/font dependency. Use pypdf for extraction.

Short-lived per-request local processes (explicitly approved), no persistent worker:
20s extraction/30s rendering; 512 MiB child memory (Linux resource limits, Windows
Job Objects). Two admitted technical operations per backend process, excess 429.
Bounded input/output, sanitized errors, no inherited app/provider secrets. Terminate
and await on timeout/cancel. Close uploads/remove owned temporary resources in finally.

Currency scope explicitly selected: current needs only. RUB/USD/EUR; changing currency
does not alter amount or request rates. Render original entered monetary string/precision.
Any new numeric interpretation uses Decimal from text, never float. Export has no
arithmetic/conversion/rounding. No unused conversion/provider/API. Rate date/provenance,
stale/missing historical rates are inapplicable without a conversion workflow. Existing
project and estimate contracts remain unchanged.

Add typed clients in frontend/lib/api and three forwarding routes. Generate OpenAPI
and TypeScript. EN/RU loading/cancel/warning/error states; extraction editable before
project save, late results cannot overwrite newer edits/uploads. Disable duplicate
downloads and release object URLs. Retain editor types/storage/preview/clipboard/date
display/reference construction. Remove browser PDF/scope readers only after callers
migrate; remove pdf-lib/fontkit/pdfjs dependencies after production AND tests migrate.
Move PDF tests/visual fixtures to backend; retire frontend visual tooling/fonts when
unused. Update locks, packaging, CI branch/check coverage, ownership/migration matrix.
Keep Compose migration ordering and frontend database independence.

## Sequence and verification matrix

1. Save plan, fetch/verify parent, branch, ignored handoff.
2. Document preparation/fonts/rendering with test-first units.
3. Owned saved/unsaved exports with immutable-data tests.
4. Bounded extraction/readers/lifecycle tests.
5. Frontend clients/routes/loading/errors/editable extraction.
6. Generate contracts; remove obsolete verified callers/dependencies.
7. Full matrix, rendered inspection, complete diff review.
8. Explicit staging, conventional commit, push child.

| Area | Evidence |
|---|---|
| Units | labels/dates/references/edits/Decimal precision/missing/no-charge/pagination |
| PDF API | own/foreign/missing/unauthenticated, binary headers/filename/cache, malformed IDs, legacy snapshots, missing CO, route precedence |
| Immutability | repeat downloads leave draft/history/project unchanged; no generation/proof/write calls |
| Unsaved | ownership/matching draft, edited values, no proof/save/provider |
| Extraction | types/MIME/UTF-8/BOM/empty/corrupt/encrypted/scanned/mixed, exact limits, warnings, timeout/cancel/cleanup |
| Visual | render and inspect all EN/RU/ES/German/long/oversized/approval/missing fixture pages, Cyrillic/Spanish |
| Frontend | affected and full units, generated contract check, TypeScript, lint, build, binary/multipart gateways |
| Backend | disposable integration, Ruff lint/format, Mypy, OpenAPI freshness |
| Containers | backend-image PDF with disposable PostgreSQL, fonts packaged, Compose validation |
| Git | full review, explicit staging, diff --check, unrelated bytes preserved |

Only disposable PostgreSQL/temporary files. Record exact commands/counts/failures,
inherited warnings and limitations. Provider failure tests are inapplicable by scope.
Rollout/rollback matching frontend+backend images together, no request fallback.
No schema/migration change; rollback preserves rows and restores browser capabilities.
Non-goals: OCR, stored uploads, microservices, persistent workers/queues, pricing or
conversion features, unrelated workflows, production deployment, broader hardening.
ANY-642 later reassesses only concrete integrated runtime/CI/deployment gaps.

## Execution evidence

2026-10-11: plan saved after Plan Mode ended; fetched main/handover, parent unchanged.
Implementation completed in the existing checkout. Saved and unsaved PDF export,
bounded temporary scope extraction and frontend integration are migrated. Currency
selection retains original values; no conversion workflow was introduced.
See [verification and runtime handoff](../any-641-verification.md) for exact commands,
test counts, all-page rendered inspection, review fixes and environment retries.
Frontend/backend images and production gateway checks pass with disposable databases;
rollback uses the matching previous image pair without database reversal.
