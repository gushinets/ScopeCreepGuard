# ANY-556: Draft dates, filtering, sorting, and CSV export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task after plan review. Steps use checkbox syntax for tracking. Read the design and constraints below before editing code.

**Goal:** Implement the approved Draft interpretation of ANY-556: UTC creation/modification dates, project/date filters, creation sorting, and CSV exports of the matching collection or the saved open Draft.

**Architecture:** Add an owner-scoped current-Draft read projection through the existing workflow route/service/repository boundaries. Collection JSON and CSV share its predicates and stable ordering; CSV serialization is a separate service module. The existing editor flush supplies the confirmed revision for individual export. Keep the current design system, routing, autosave controller, and result tabs.

**Tech stack:** Python 3.12, FastAPI/Pydantic, SQLAlchemy Core/text with bound values, PostgreSQL 17, Python `csv`/`decimal`; React 19/TypeScript, React Router, Base UI, use-intl, Vitest. No new runtime dependency or worker.

**Spec:** The user's approved ANY-556 specification in this chat, captured in the scope, API, CSV contract, and acceptance tasks below. Historical issue wording about History does not define this implementation's scope.

## Baseline, checkout, and handoff

- Planning date: 2026-10-24.
- Repository: `gushinets/ScopeCreepGuard`; target PR base: `main`.
- Exact fetched main base: `43b0f4bcc3605b571caefa843706a4b752b46560`.
- Branch: `codex/any-556-draft-filters-csv`, created directly from that SHA.
- Isolated checkout: `D:\.codex\worktrees\any-556-draft-filters-csv\ScopeCreepGuard`, created using the Codex worktree tool. Initial status was clean.
- Original checkout: `D:\Devpy\ScopeCreepGuard`, branch `codex/predictable-docker-startup`, HEAD `1d73574f373b63a5bbeb8635fa16f32d8ff7aebb`. Preserve its untracked `docs/architecture/2026-10-23-nine-issue-acceptance.md`, `docs/architecture/evidence/2026-10-23-nine-issue-acceptance/`, and `docs/architecture/plans/2026-10-23-nine-issue-acceptance.md`.
- PR [#42](https://github.com/gushinets/ScopeCreepGuard/pull/42) is merged; its merge commit is the chosen baseline. No unmerged infrastructure dependency and no feature-branch base.
- Applicable instructions: root `AGENTS.md`, `frontend/AGENTS.md`, and this directory's README. Future implementation and evidence stay in the isolated checkout. No reset, stash, unrelated commits, or overwrites.
- Frontend instructions mention installed Next.js docs, but the baseline frontend is Vite/React; neither this checkout nor the original checkout has `frontend/node_modules/next/dist/docs`. No Next.js APIs or conventions are needed. Recheck installed documentation before any Next-related work; do not install Next to satisfy a stale instruction.
- Native plan execution is proposed because the API, generated contract, editor, and collection UI share interfaces. An independent review checks the plan before implementation; final review checks the finished branch.

## Scope and global constraints

- Work exclusively within current Drafts. Preserve Projects, immutable History, one current Draft per project, automatic saving, user edits, client-material languages, and agreement lifecycle.
- Exclude archived projects and foreign owners on every new collection/export read. Do not use compatibility Draft mappings or a History join as the source.
- No accuracy feedback, client communication outcomes, analytics, AI calls, restoration features, new queue, or snapshots.
- Export reads must not mutate Draft timestamps/revisions, projects, analysis, History, events, sessions, or business metrics. The required pre-export editor flush is an ordinary existing save.
- Reuse `drafts.created_at` and `drafts.updated_at`. Do not backfill dates with migration time or add duplicate columns.
- RU/EN interface and CSV labels; client material remains in its saved language. UTC for date filtering and displayed/exported timestamps.
- Preserve unrelated tracked/untracked files and private worklogs. Do not change Linear descriptions/statuses. Create a PR against `main`; do not merge or deploy.
- Use documented Compose entry points and migration gate. Unique test project, disposable data, private test object storage, both workers. Never reset existing databases or remove volumes without explicit authorization.
- Update `ci/contracts/openapi.json` and regenerate `frontend/src/shared/api/generated.ts` using repository tools; never edit generated types by hand or weaken freshness checks.

## Findings and design decisions

### Current behavior confirmed on the baseline

- `my-drafts-view.tsx` displays project, request preview, verdict, and creation date only. It has basic loading/error/empty handling and ignores responses after unmount.
- `workspace.tsx:listDrafts` calls `/api/v2/projects`, then one Draft endpoint per project using `Promise.all`. `DraftListItem` has both timestamps but no project ID. No `/api/v2/drafts` collection endpoint exists.
- `editor.ts:flush` returns `DraftAutosave.flush()` and therefore the confirmed `WorkingDraft`; flush drains edits queued during an in-flight save. Failure retains edits/recovery data and exposes existing retry feedback.
- `ScopeCheckView` renders the workspace heading even without analysis. `ResultPanel` renders no result UI for an unanalyzed Draft. Put individual export beside the existing workspace heading controls, not solely inside a result tab.
- Working documents store selected/edited reply in `draftDocument.reply.text`, language in `.reply.language`, and commercial fields in `.changeOrder`. Analysis explanation is `analysisRun.resultSnapshot.reasoning`.
- `services/drafts/workflow.py:enrich` loads one analysis run in a separate unit of work. Do not call it once per collection row; use a single set-based query with a left join to the current `last_analysis_run_id`.
- Current mappings are catalog-driven from `0008_contextual_onboarding_schema.json`. Existing indexes include `projects_owner_listing(user_id, archived_at, created_at DESC)`, unique `drafts_one_per_project(project_id)`, and `drafts_project_created_at_idx(project_id, created_at)`.
- Legacy `database/queries/drafts.py` joins History; legacy `models/drafts.py` explicitly describes compatibility data. Leave these and legacy routes unchanged.
- Existing collection endpoints return full arrays; pagination is optional in the request. Implement pagination explicitly for Drafts so the export-beyond-visible-page requirement is demonstrable.

### Approach

One shared server-side current-Draft projection fits the approved scope. Browser aggregation cannot guarantee authoritative collection/export parity and repeats N+1 reads. A History-backed export would change the meaning of Draft. Neither is an acceptable alternative.

**Implementation choices proposed here:** 50-row collection pages, maximum 100; offset pagination; URL-backed filter state; Base UI popover/dialog; a confirmed-revision guard for single export. These are builder decisions, not previously approved product requirements.

### API and read interfaces

Add these GET operations to `apps/api/src/scope_guard_api/routes/workflow.py`, with static `/drafts/export.csv` registered before `/drafts/{identifier}`:

| Route | Query | Response |
| --- | --- | --- |
| `/api/v2/drafts` | `projectId?: UUID`, `createdFrom?: YYYY-MM-DD`, `createdTo?: YYYY-MM-DD`, `sort: newest\|oldest = newest`, `limit: 1..100 = 50`, `offset: integer >= 0 = 0` | `{drafts: DraftCollectionItem[], total: integer, hasDrafts: boolean}` |
| `/api/v2/drafts/export.csv` | Same project/date/sort filters, `locale: en\|ru = en`; no pagination | CSV containing all matching rows |
| `/api/v2/drafts/{identifier}/export.csv` | `locale: en\|ru = en`, `expectedRevision?: positive bigint string` | CSV header + one current saved Draft row; 409 if the supplied revision differs |

`DraftCollectionItem` contains `id`, `projectId`, `projectName`, `requestPreview` (first 160 characters), `verdict` (nullable), `createdAt`, `updatedAt`. `total` counts matching Drafts before pagination. `hasDrafts` means this owner has at least one current Draft in an active project, ignoring filters; it separates no Drafts from no matches even with a filtered deep link. Count/list metadata must use one SQL statement/snapshot rather than unrelated reads that can contradict each other.

Use a Pydantic query model in `schemas/workflow.py` with explicit aliases and a shared `DraftCollectionFilter` domain value in a new `domain/drafts/collection.py`. Validate exact date-only syntax, UUIDs, sort, pagination, and from <= to. Reject `createdTo=9999-12-31` as out of supported range because its exclusive next day cannot be represented; document that boundary. Route validation uses the existing localized invalid-request response convention, not raw internal exceptions. API filter parser is reused by JSON and collection CSV.

Repository additions in `WorkflowRepository` / `WorkflowSQLRepository`:

- `draft_collection(owner: UUID, filters: DraftCollectionFilter, *, limit: int | None, offset: int = 0) -> dict` returns detached `{drafts, total, hasDrafts}`. Internal rows include only current Draft fields, project name, and joined analysis result needed by the service; JSON response maps to summaries.
- `draft_export_row(owner: UUID, identifier: UUID) -> dict` returns the same internal projection for one owned active-project Draft or uniform `draftNotFound`/404.
- `WorkflowService.draft_collection(owner, filters, *, limit=50, offset=0) -> dict` maps summaries; `export_drafts_csv(owner, filters, locale) -> bytes` uses unlimited matching rows; `export_draft_csv(owner, identifier, locale, expected_revision=None) -> bytes` verifies revision and serializes one row. Reads open a unit of work without commit/event calls.

Share an explicit projection and predicate builder inside the workflow repository. SQL uses `drafts d JOIN projects p ... LEFT JOIN analysis_runs a ON a.id=d.last_analysis_run_id AND a.project_id=d.project_id`. Scope by `p.user_id=:owner AND p.archived_at IS NULL AND d.revision IS NOT NULL`. Never select credentials, provider model/telemetry, or whole internal run JSON for CSV. Bind owner, identifiers, dates, limit/offset. Choose ordering from two literal trusted expressions: `d.created_at DESC,d.id DESC` or `d.created_at ASC,d.id ASC`; no user text in SQL ordering.

For inclusive date ranges use `created_at >= from 00:00:00 UTC` and `created_at < (to + 1 day) 00:00:00 UTC`. Foreign, nonexistent, and archived project filters all produce identical empty collection/header-only export behavior. Individual foreign/nonexistent/archived Drafts all return the same 404. Collection/export share these exact predicates. Pagination uses a deterministic ID tie-breaker; independently executed requests observe current saved data, not a frozen cross-request snapshot.

### UI and autosave integration

- Add `model/collection-client.ts` for typed query encoding, list responses, and authenticated CSV fetch/download using shared `apiFetch` with `cache: 'no-store'`. New DTO types reference generated API types, with a deliberate adapter to existing `DraftListItem` if needed.
- Extend `DraftsValue.listDrafts(filters, pagination)` and `DraftsValue.exportCurrentDraft(locale): Promise<void>`; replace browser N+1 composition in `workspace.tsx`. Collection loading does not flush or save a Draft. Collection CSV fetch is independent of the page currently loaded.
- Put Filter and Export at the collection heading's upper right, wrapping on mobile. `draft-filters.tsx` uses the installed Base UI Popover; labeled native project/date/sort controls, local pending form values, Apply, Clear/reset, and date validation. Escape/outside-close and return focus to trigger; error is announced and focuses the first invalid date.
- Store applied filters in namespaced URL keys `draftProject`, `draftCreatedFrom`, `draftCreatedTo`, `draftSort`; omit default values. Keep unrelated search params/hash/state and existing `draft`/`historyProject` behavior. Reset pagination on filter changes. Routing already retains search across collection -> open -> return. Back/forward restores filters and valid page state. Invalid filter URLs expose a localized error/reset rather than silently substituting a broad collection.
- Keep load identity/cancellation per filter/page request; clear loading errors on a fresh load and prevent delayed prior responses from replacing newer rows. Show separate no-Drafts, no-matches with Clear, and load-failed with Retry states. Provide previous/next page controls using total; tolerate collection shrink by returning to a valid page.
- Display explicitly labeled Created (UTC) and Modified (UTC) timestamps using localized date format plus hours/minutes/seconds and `timeZone: 'UTC'`, with semantic `<time dateTime>` values. Stable order uses creation date, never modification date.
- `draft-export-dialog.tsx` explains collection CSV contains current saved Drafts matching the applied filters/order, across all pages. Capture that filter selection when opening, label pending/error state, allow retry, and do not create History or PDF exports. Empty matching export remains available and downloads headers only.
- `draft-export-action.tsx`, exported through Drafts public index, appears in `ScopeCheckView`'s heading beside existing edit-project control. Available with a current active Draft before analysis/agreement exists. Hide in legacy-only/History views; disable for archived projects and unresolved recovery. Existing result tabs remain untouched.
- Individual export captures controller identity/navigation generation, calls `editor.flush()`, and only downloads for the still-active controller after successful flush. Include returned `saved.revision` as `expectedRevision`. If another tab advances the server, show localized retry/error instead of claiming the CSV includes this tab's confirmed revision. Do not reinstall server data or overwrite edits on export.
- If edits occur while the download is in flight, keep them and abort the misleading download when controller/edit identity changes; ask the user to retry through an ordinary localized message. A flush failure must issue no CSV GET and no download; preserve existing `SaveFeedback` retry/recovery behavior. No manual-save requirement or new save state machine.
- Add RU/EN messages in the existing message JSON files; use existing button/input/layout tokens and Base UI primitives. No Projects/History restyling or result-tab redesign.

### CSV schema and safety contract

Both endpoints use the following fixed column order. Header names and verdict/boolean categorical values depend on interface/export locale; the saved client language tag and ISO currency code remain canonical values. ISO language/currency identifiers do not change stored language or amount.

| # | EN header | RU header | Current saved source |
| --- | --- | --- | --- |
| 1 | Draft ID | ID черновика | `draft.id` |
| 2 | Project ID | ID проекта | `draft.projectId` |
| 3 | Project name | Название проекта | current `project.name` |
| 4 | Draft created at (UTC) | Черновик создан (UTC) | `draft.createdAt` |
| 5 | Draft updated at (UTC) | Черновик изменён (UTC) | `draft.updatedAt` |
| 6 | Draft revision | Ревизия черновика | `draft.revision` as exact decimal integer text |
| 7 | Current client request | Текущий запрос клиента | `draft.requestText` |
| 8 | Analysis verdict | Результат анализа | linked analysis `resultSnapshot.verdict`, localized |
| 9 | Analysis explanation | Объяснение анализа | linked analysis `resultSnapshot.reasoning` |
| 10 | Analysis is stale | Анализ устарел | `draft.analysisIsStale`, Yes/No or Да/Нет |
| 11 | Selected client reply | Выбранный ответ клиенту | `draftDocument.reply.text`, including edits |
| 12 | Client-material language | Язык материалов для клиента | `draftDocument.reply.language` |
| 13 | Additional-work description | Описание дополнительных работ | `draftDocument.changeOrder.description` |
| 14 | Estimated hours | Оценка часов | `.changeOrder.estimatedHours` exact saved decimal text |
| 15 | Additional amount | Сумма за дополнительные работы | `.changeOrder.additionalCost` exact saved decimal text |
| 16 | Currency | Валюта | `.changeOrder.currency` |
| 17 | Without additional payment | Без дополнительной оплаты | `.changeOrder.noAdditionalCharge`, explicit localized boolean |
| 18 | Schedule change | Изменение сроков | `.changeOrder.timelineImpact` |

- Missing optional values, absent analysis/agreement, and missing commercial fields are blank. When no change order exists, column 17 is blank, not No. Export analysis staleness exactly as saved, including true when no analysis exists; do not recompute/mutate it.
- Verdict labels: EN `In scope`, `Borderline`, `Out of scope`; RU `Входит в объём работ`, `Спорный случай`, `Выходит за рамки работ`. Saved request/reply/explanation/terms are never translated by export.
- Never fill terms from analysis prose, preliminary estimates, or project defaults; only the current explicit editor fields supply commercial values. Money/hours never pass through binary float; preserve saved strings including meaningful trailing zeros. Do not replace decimal dots or round values to accommodate the CSV delimiter.
- Serialize with Python `csv.writer`, `newline=''`, CRLF records, standard quote escaping, UTF-8 BOM. RU delimiter `;`; EN delimiter `,`. Preserve multiline/Unicode/quotes/delimiters.
- Formula safety applies to every string cell, including names, request, reasoning, reply, language, and commercial text. Find the first character after leading Unicode whitespace and Unicode Cc/Cf characters; if it is `=`, `+`, `-`, or `@`, prefix a single ASCII apostrophe to the entire original value. Retain the original whitespace/text after that prefix. This deliberately changes hazardous spreadsheet cell text; CSV quoting alone is insufficient. Typed valid numeric/UUID/timestamp cells contain only their validated canonical values. Unit tests must pin all transformation classes, including tab, CR/LF, nonbreaking space, zero-width/BOM prefixes, full-width text, and safe leading apostrophes.
- UTC timestamps use ISO 8601 with explicit `Z` and existing fractional precision; do not invent historical values.
- Response: `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="drafts-en.csv"` / `drafts-ru.csv` or `draft-<UUID>-<locale>.csv`; filenames use only constants and validated UUID/locale. Set `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff` on successful CSV responses; verify error privacy headers too.
- A collection returns one header plus one row per matching current Draft; no matches means BOM + header only. Individual export returns one header and one row. No internal JSON blobs, credentials, telemetry, or unrelated account data.

### Migration rationale

Initial decision: no migration. Both timestamps are required `timestamptz` columns; the unique project Draft constraint bounds the active collection to one row per owned project. The existing owner listing and project/Draft indexes support the scoped join. Task 1 records actual `EXPLAIN (ANALYZE, BUFFERS)` for project-specific, all-project, date-range, and both-sort queries with representative disposable fixtures. Small-fixture sequential scans are not by themselves evidence that an index is missing. Only measured, justified schema support warrants an Alembic revision, matching catalog manifest, schema-verifier updates, and migration tests; record that decision before implementing such a change.

## Review focus

1. Edits/new navigation during flush or CSV fetch must not download the wrong Draft or overwrite newer text (Task 4).
2. Recovered unsaved edits and definitive save failures must not produce an apparently current download (Task 4).
3. Equal creation timestamps and deletion/archive between collection requests must yield deterministic ordering and safe pagination/empty states (Tasks 1 and 3).
4. Invisible Unicode prefixes before formula operators must be guarded while exact decimals/multiline content survive a CSV round trip (Task 2).
5. Invalid or foreign filter deep links must not silently expose an unfiltered account-wide download; selected filters must survive open/return/back navigation (Tasks 2 and 3).

## Ordered implementation tasks

### Task 1: Owned current-Draft collection and query plan

**Files:** Create `backend/src/scope_guard/domain/drafts/collection.py` and `backend/tests/integration/test_draft_collection.py`; modify `domain/drafts/workflow_repository.py`, `database/repositories/workflow.py`, `services/drafts/workflow.py`, `apps/api/src/scope_guard_api/schemas/workflow.py`, and `apps/api/src/scope_guard_api/routes/workflow.py` at their repository-relative existing paths.

**Interfaces:** Produce `DraftCollectionFilter`, repository `draft_collection` / `draft_export_row`, service `draft_collection`, and `DraftCollectionItem` / collection response/query DTOs described above. Consume existing `WorkflowError`, detached wire mappings, and `WorkflowWork`.

- [ ] Write real-PostgreSQL failing tests using existing `disposable_url` and `WorkflowService` project/Draft creation with a generator that fails if called. Seed two owners, active/archived projects, midnight UTC boundaries, and equal timestamps. Assert IDs, counts, `hasDrafts`, exact order, project/date combined filters, limit/offset, empty owner, and owner isolation.
- [ ] Run `uv run pytest tests/integration/test_draft_collection.py --require-integration -q` from `backend`; confirm the new interfaces are missing rather than fixture failures.
- [ ] Implement the shared scoped projection and bounds through repository/service; add JSON route and typed validated query model. Cover an empty page separately from zero matches and use a single statement for response metadata consistency.
- [ ] Add API tests in `backend/tests/api/test_workflow_v2.py` for auth, malformed/empty dates, datetime instead of date, leap days, reversed/max-date ranges, UUIDs, sort injection/unknown values, negative/oversize pagination, and uniform foreign/archived project behavior. Pin the repository's established 400 validation convention.
- [ ] Run focused API/integration tests and capture EXPLAIN plans on representative data. Write the migration/index decision in the verification report. Commit only Task 1 source/tests when passing.

### Task 2: Shared CSV serializer, export routes, and generated contracts

**Files:** Create `backend/src/scope_guard/services/drafts/csv_export.py`, `backend/tests/unit/test_draft_csv_export.py`, and `backend/tests/integration/test_draft_csv_exports.py`; modify workflow service/routes/schemas, `backend/tests/api/test_workflow_v2.py`, `ci/contracts/openapi.json`, and generated `frontend/src/shared/api/generated.ts` through tooling only.

**Interfaces:** Produce `render_drafts_csv(rows: Iterable[dict], locale: Literal['en', 'ru']) -> bytes`, service `export_drafts_csv` / `export_draft_csv`, and the two GET routes defined above. Consume Task 1 projection and filter parser. No PDF export service or object storage involved in CSV generation.

- [ ] Write failing unit tests with `csv.reader` round trips for all 18 columns and their RU/EN labels/values, BOM/delimiters, multiline request and edited reply, quotes, emoji/Cyrillic, all formula-prefix classes, empty collection, no analysis/change order, explicit false/true, and exact `123456789012345.67`/`2.50` strings.
- [ ] Run `uv run pytest tests/unit/test_draft_csv_export.py -q`; confirm missing serializer failure. Implement serialization and pure safety transformation as specified.
- [ ] Write failing integration/API tests asserting collection/CSV IDs and order agree for every filter/sort, 51+ matching rows are all exported despite limit 50, filtered no-match headers only, single unanalyzed Draft export, saved revision check, private response headers, safe filename, and static route precedence. Reuse existing controlled analysis fixtures to prove edited reply/terms win over generated values without paid calls.
- [ ] Implement CSV service/route reads. Do not expose unrestricted run data in responses. Assert foreign/missing/archived single reads are uniform and locale/query validation cannot bypass ownership.
- [ ] Snapshot Draft/project/revision/run/History/change-order/export/activity/session/metrics tables before and after both export GETs; assert unchanged state, timestamps, revisions, and row counts. Save before export is tested separately as an ordinary mutation.
- [ ] Regenerate OpenAPI: from `backend`, `uv run python scripts/export_openapi.py --output ../ci/contracts/openapi.json`; from `frontend`, `corepack pnpm api:types`. Assert OpenAPI describes CSV media type/content disposition and filter query parameters. Run both freshness checks and `tests/unit/test_openapi_export.py`.
- [ ] Run focused tests, Ruff, and mypy for touched backend code; commit only this task's source/tests/generated contracts.

### Task 3: Draft collection controls, dates, and persisted filter state

**Files:** Create `frontend/src/features/drafts/model/collection-client.ts`, `frontend/src/features/drafts/draft-filters.tsx`, `frontend/src/features/drafts/draft-export-dialog.tsx`, and `frontend/src/features/drafts/my-drafts-view.test.tsx`; modify `my-drafts-view.tsx`, `model/types.ts`, `context.ts`, `app/workspace.tsx`, and RU/EN message JSON. Add a focused query/client test if encoding/download behavior needs independent assertions.

**Interfaces:** `DraftFilters = {projectId?: string; createdFrom?: string; createdTo?: string; sort: 'newest' | 'oldest'}`; `listDrafts(filters, {limit, offset})` returns generated collection DTO; `downloadDraftCollection(filters, locale): Promise<void>` uses Task 2 CSV GET. `DraftListItem` adds `projectId` and aligns with generated summary type. Applied URL state is authoritative; transient popover edits are local.

- [ ] Write failing UI tests for initial/default listing, RU/EN UTC timestamp labels including seconds, popover controls/apply/reset, combined filters, both sorts, page changes, header-only export, distinct empty/no-match/error states, retry, and stale response suppression using controllable promises.
- [ ] Run `corepack pnpm test -- src/features/drafts/my-drafts-view.test.tsx` from `frontend` and confirm feature assertions fail before implementation.
- [ ] Implement client/query encoding, replace N+1 `listDrafts`, and add collection UI using existing Base UI, buttons, and layout tokens. Export dialog captures applied filters and excludes limit/offset from download. Use authenticated `apiFetch`, release object URLs after download, preserve filename safety.
- [ ] Add integration assertions to `persistent-navigation.test.tsx` and relevant request fixtures in `persistent-store.test.tsx`: filters/unrelated params/hash/history state survive open/return/back; invalid links show reset/error; collection failures do not replace editor state; account changes do not retain prior account results.
- [ ] Add keyboard/focus tests: Tab reaches each control, Escape returns focus, dialog traps/restores focus, date errors are labeled/announced. Test archive/removal while on the last page and filter reset after no matches. Keep mobile wrapping assertions for actual browser review.
- [ ] Run focused UI/navigation/store tests, typecheck, lint/boundary checks, and message parity checks used by existing tooling; commit passing Task 3 files only.

### Task 4: Export the saved open Draft through autosave

**Files:** Create `frontend/src/features/drafts/draft-export-action.tsx` and `frontend/src/features/drafts/draft-export-action.test.tsx`; modify `app/workspace.tsx`, `features/drafts/context.ts`, `features/drafts/index.ts`, `features/analysis/scope-check-view.tsx`, collection client, RU/EN messages, and focused cases in `frontend/src/test/persistent-store.test.tsx`. Existing autosave/editor code is reused; modify it only if a focused test demonstrates a missing integration hook.

**Interfaces:** Add `exportCurrentDraft(locale: Locale): Promise<void>` to Drafts context and a public `DraftExportAction` component. It consumes existing controller/flush/navigation/edit tokens and `downloadDraftCsv(id, locale, confirmedRevision)` from the client module. Do not make `DraftsValue.saveDraft` a new user requirement.

- [ ] Write failing tests: action exists without analysis/agreement; typed request/reply/terms are persisted before CSV GET; the GET contains confirmed revision; CSV fetch/download never starts on save rejection; edits and existing Retry remain available; successful retry exports the current saved edit.
- [ ] Add pending-save/newer-edit tests proving flush drains newer queued changes; navigation/controller replacement cancels download; edits made during CSV fetch retain local values and prevent a misleading download; revision mismatch shows error without stale download; archived/legacy/recovery states cannot export as current.
- [ ] Run focused tests to establish failures. Implement the export command and action, placing it in the workspace heading for both analyzed and unanalyzed Drafts. Reuse `SaveFeedback`; no manual save button, History writes, or AI operations.
- [ ] Run Draft action, persistent store/navigation, `autosave.test.ts`, and `autosave-recovery.test.ts`; verify existing generation/tone/language edit protection and retry behavior still pass. Run typecheck/lint and commit passing Task 4 files only.

### Task 5: Full verification, documentation, and PR

**Files:** Create `docs/architecture/2026-10-24-any-556-draft-csv-verification.md`, `docs/architecture/evidence/2026-10-24-any-556/`, and `docs/design/draft-filtering-csv.md`; update this plan's checkboxes/decisions and docs index as appropriate. Add reproducible feature acceptance automation under `tests/e2e/` following existing test runner conventions; keep fixture generation scoped to disposable test data.

- [ ] Run backend `uv run pytest --require-integration`, Ruff check/format check, mypy, and OpenAPI freshness from README. Run frontend `corepack pnpm test`, lint, typecheck, API-type freshness, and build. Record exact commands/exit codes/counts; failures are not passes. A baseline failure is recorded and investigated before attributing it to this change.
- [ ] Create a unique `scg-any556-test-<UUID>` Compose project with the documented `compose.yaml`; use empty test env files, synthetic auth/provider settings, dynamically allocated ports, and a private test storage fixture following `verify_docker_startup.py`/existing S3 tests. Do not invent overlay combinations or alter migration targets. Start PostgreSQL -> one-shot migrate -> backend/workers -> frontend through documented dependencies; verify both workers healthy and storage private. Submit no paid AI operations.
- [ ] Before acceptance, record base SHA, tested committed revision, any tracked/untracked local source modifications and their diff/hash, Docker/Compose versions, freshly built image IDs and `org.opencontainers.image.revision` labels. Assert containers run those images. Include worker/migration evidence even though CSV itself is synchronous.
- [ ] In a real browser create two owners and multiple projects/current Drafts through the UI. Use controlled disposable PostgreSQL fixtures for exact creation boundaries/ties and analysis-dependent fields, leaving actual editing/autosave in the browser. Verify desktop/mobile layouts, keyboard/focus, UTC dates and modification changes, filters/reset, sorting, all-page collection download, no-match/empty/error states, open-edit-export, and failed-save retry with no stale download.
- [ ] Compare downloaded CSV bytes/rows to PostgreSQL current content and the confirmed revision for both locales. Verify missing analysis export, exact decimals, archive/owner isolation, and no export side effects. Recheck Projects/History navigation, immutable saved History, one current Draft, and existing language/edit protection. Keep screenshots, query plans, test outputs, and an evidence manifest using synthetic data only.
- [ ] Document filter parameters/pagination, inclusive UTC ranges/seconds, CSV field order/localization, exact formula-safety transformation, date maximum, current saved state/race limitations, migration rationale, and failure/retry behavior. Distinguish unit/component/full-stack/browser results.
- [ ] Stop only this task's owned test containers when finished; retain test volumes unless explicitly authorized to remove them. Never use general Docker prune/down-volume cleanup. Preserve original acceptance reports and all unrelated files.
- [ ] Use `superpowers:verification-before-completion` and request a whole-branch code review. Address actionable defects and rerun affected checks. Record unresolved environmental limitations explicitly; do not claim unexecuted checks passed.
- [ ] Commit the feature, tests, generated contracts, plan, public docs, and sanitized evidence. Verify branch ancestry directly from exact main base, inspect staged diff for unrelated/private files, and check original checkout still has its acceptance work untouched.
- [ ] Push `codex/any-556-draft-filters-csv`, create a PR against `main`, and attach it to this chat. State that approved Draft semantics replace ANY-556's historical History wording. Include exact base/tested SHAs, source/image evidence, actual checks and limitations, no-migration rationale, and merged infrastructure PR #42. Do not merge/deploy or change Linear.

## Planning preflight evidence and current status

- Git inspection completed; original checkout had only the three unrelated untracked acceptance paths described above.
- `git fetch origin` succeeded after requesting permission to update repository metadata; origin/main advanced from `0bea6bc8c2e106f78dd2a14cbff4cb0b7e4c3d90` to the chosen `43b0f4b...` base.
- GitHub PR metadata confirms #42 merged at 2026-10-24 13:45:43 UTC into main.
- Native worktree created and requested branch created at exact base; no product code, dependencies, schemas, contracts, or tests changed during planning.
- Docker Engine read check succeeded with permission: **29.8.2**; Compose **5.6.0**. Initial restricted Docker pipe access failed; this was an access restriction, not an application failure.
- Tests/builds/query plans/browser acceptance have **not run** during planning. Existing infrastructure verification is background context, not proof of ANY-556 behavior.
- Plan status: ready for independent builder review, then user plan review under the requested Superpowers workflow. Implementation steps remain unchecked.

## Follow-up ownership and limitations

- Implementer owns Tasks 1–5 and evidence/PR accuracy; reviewer owns independent scope/correctness feedback. User owns plan review and any requested change in scope.
- No unresolved product question is needed to write this plan. Pagination size, URL keys, explicit revision guard, and upper date boundary are proposed choices that can be corrected at review.
- Large exports initially materialize the matching collection in memory; document this limitation and measure representative data. Do not add jobs or truncate rows silently. If measurements require streaming, retain the same shared query predicates and flat CSV contract, with a read transaction that closes on cancellation.
- Exports reflect current saved state at query time; collection listing and later export are separate reads. No cross-request snapshot, historical reconstruction, or recovery export is promised.
