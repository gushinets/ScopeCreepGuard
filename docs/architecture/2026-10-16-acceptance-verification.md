# 16 October acceptance correction verification

Implementation and deterministic verification are complete. Paid live-model
verification and the real-data rollout remain blocked/unperformed as stated below.
This document supersedes the 15 October verification only for the final tree and
scenarios explicitly recorded below; it does not claim ticket acceptance.

## Version and preservation

Existing checkout, `codex/any-688-output-validation`, no upstream. Base/HEAD
`4450ecacc89f7fd67fc62cdaf3bdc740dc4988cb`; all corrections remain uncommitted.
The reviewed `f00e1014c376cba9e5dc65e73421a98c3aa3c37e` has the same committed
tree `b98addef87889fa5fc02f4ec9d6249e49e74a3f5`, with four different commits on
each side of the common ancestor `bd3fa73`. Fetched origin refs without switching,
pulling or rebasing. Preserved all inherited uncommitted ANY-688 work, unrelated
`.gitignore` edits, the repository review and both local design documents.
No commit, push, merge, PR, Linear mutation or application database migration.

Plan: [acceptance completion](plans/2026-10-16-any-688-acceptance-completion.md).
Generation prompt/validation version is `workflow-v5`. Completed old results stay
readable; pending v1–v4 work fails before dispatch/accepted-stage reuse. Drain with
the original matching worker before deploying v5 when pending work must finish;
never rewrite existing operation versions, hashes, counters or reservations.

## Acceptance evidence and concrete corrections

Read the latest 15 October comments on ANY-543/635/553/554/548 and ANY-688 (no
comments). Retrieved the ANY-635 reviewer ZIP, verified SHA256
`43d7d9b8f3de12e9012a61079c8fd3d74f8f80f0e01b1479597c0fc335b82d26`.
Archive and replay files are ignored under `output/acceptance-2026-10-16/reviewer/`.
The 14 failed live full checks were blocked at CO, while ordinary analysis/reply
languages passed. Nine live regenerations on synthetic saved results, six actual
PDF exports/eleven inspected pages and passed dropdown controls retain their own
limited successful meaning; they are not counted as new final-version runs.

* Valid catalog labels: EN/RU/ES and regional variants use complete reviewed
  server-owned labels. Their model schema contains only CO prose/applicability;
  no label generation/corrections are needed. The assembled envelope still has
  every label for preview/Copy/PDF. Other supported languages retain a full native
  label schema: independent foreign/mixed checks, target support, contextual group
  language and the single ledger-accounted semantic review. Uncertain semantics
  correct/fail. No global confidence threshold reduction. Actual failed headings
  (including “Change Order Document Number”, “Дата создания документа”, “Folio de
  la orden de cambio”) are regression fixtures.
* Manual price: amount/currency merge atomically. Effort is preserved independently;
  explicit free-work selection survives. Suggestions remain in `aiValues` with
  their own currency/rationale. Manual ownership markers in that existing
  representation survive reload and coincidentally matching suggestions; the
  public schemas/parsers/types accept these additive keys. An AI rationale is
  cleared from the displayed manual price, while a manual rationale is preserved.
  Worker, compatibility merge, frontend merge and restored initial editor state
  use the same policy. No conversion occurs.
* D1: inspected all three original candidates and feedback, not only the terminal
  error. Attempts one and three appended stale 8 hours/240 USD to manual saved
  text and were rightly rejected. Attempt two faithfully translated the saved
  description, but “3 business days after approval” was falsely rejected at
  language confidence 0.6842. The reviewed short schedule grammar fixes that
  false rejection without a general prose exemption. Translation input excludes
  the competing older analysis estimate; saved manual text and terms govern.
* Translation preservation combines localized amount/currency/unit occurrence
  bindings and contextual review of identifiers, dates, scope and incidental
  numbers. Raw numeric-substring set equality is no longer its authority. Common
  RU/EN/ES compound number words and localized grouping/decimals are covered;
  semantic review remains necessary for arbitrary prose/other languages.
  Empty saved fields remain empty. Failed replacement preserves the saved revision.
* Schedule review covers quantity/unit, working versus calendar basis, approval
  or other start condition, absolute/relative dates and conditional versus binding
  promises. Deterministic recognized RU/EN/ES bindings include singular Russian
  forms. Conditional numeric working-day proposals reach the existing bounded
  reviewer, consistently with number-word proposals. No new review/repair loop.
* Missing data: RU/EN field guidance identifies parties, description, effort,
  paid amount/currency and schedule (or revised end date). Preview/Copy/PDF mark
  incomplete documents, using client-language labels; email and approval date
  remain optional. Warnings do not discard drafts or block every export.
  Finalization preserves established blocking rules and returns `fields` for
  invalid description/paid amount/currency or invalid effort. Parties/schedule
  are warnings, not newly imposed API requirements. Explicit free work permits
  absent amount/currency. The frontend displays finalization fields.
* Inherited ANY-688 safeguards remain: derived input detection preserves raw
  requests/URLs/emails/code; override, fallback/reset/restore; stricter output
  language; actual scope/concession review; cosmetic regeneration rejection;
  malformed/uncertain decisions, correction/exhaustion and saved-content protection.

The independent read-only review found four Important issues: ownership collision,
compound number words, singular Russian schedules and conditional numeric working
days. Each was reproduced with a failing test, corrected and covered by the focused
46-case backend suite. No Critical issue was found. The reviewer did not evaluate
live model accuracy, browser/PDF evidence or a real deployed rollout.

## Supported runtimes and coordinated deployment

Runtime inventory: Settings defaults disable `workflow_v2`/`llm_workflow`; the
Next page chooses its persistent provider from `SCOPE_GUARD_WORKFLOW_V2` at runtime.
`compose.services.yaml` supplies common services, `compose.yaml` is the ordinary
entry point, `docker-compose.yml` includes it, and `docker-compose.dokploy.yml`
is the production entry point. `compose.workflow.yaml` adds persistent frontend/
API and export worker; `compose.llm.yaml` adds durable admission/LLM worker and
requires explicit shared database, model and price bounds. There is no tracked
custom launcher in `scripts/`; historical ignored launchers are not rollout proof.

The only supported successful generation runtime is persistent + durable LLM.
Legacy-compatible HTTP generation adapters still accept keyed owned Draft context
under that runtime and use the same worker/History publication. Direct generation
is retired: default legacy requests receive 503 `workflowUnavailable`; a persistent
API without durable LLM returns the same upgrade failure. Already-retired unkeyed
legacy routes under v2 retain 426. No provider fallback and no successful unsaved
analysis remains selectable through a public generation route. Existing reads,
manual editing and historical data are retained where their API is supported.
RU/EN errors explain the coordinated upgrade, rather than asking users to save
after a purported successful check. Database startup guards remain unchanged.

Operator rollout (not performed here): stop/drain old generation, back up data,
use the guarded Alembic procedure through `0005_llm_workflow` (including the
existing legacy-adoption/backfill procedure when applicable), verify catalog and
ownership, then deploy matching v5 frontend/API/LLM worker and export worker.
Activate both workflow flags together, use matching auth secret/public Origins/
shared database, private export storage, explicit supported provider model and
valid conservative input/output price bounds. Never enable flags against an
unmigrated database. API/LLM workers validate schema; they do not migrate it.
Compose migration ownership remains the documented operator/entrypoint behavior.

## Verification execution and limits

Only synthetic customer data and owned disposable PostgreSQL databases were used.
Provider outputs/review decisions in deterministic suites and browser stack are
controlled HTTP fixtures through the real native bridge/gateway/ledger. They prove
mechanics for those candidates, not real-model judgment accuracy.

Initial failing tests: 13 heading/schema/localized cases failed and one D1 negative
control passed; frontend merge six failed/two passed. Later reviewer counterexamples
failed before corrections. Missing-module collection errors and environmental
failures are not counted as product-reproduction test failures.

Completed final results: backend unit/API/architecture 596 passed (82.93 s);
all PostgreSQL integration tests 80 passed (1034.02 s); repeated final SQL journey
3 passed (45.67 s); final frontend 357 tests/49 files (48.91 s), TypeScript and
production build passed. Backend Ruff passed; frontend ESLint has no errors and
one inherited unused `_s` warning. Both mypy platforms passed (201 sources).
Generation gateway passed actionable retirement/no-call checks and retained saved
fixture read/edit/reload/dedup/ownership checks. The complete integration rerun
replaced two old tests expecting retired public generation to succeed: synthetic
legacy fixtures are now explicitly seeded through test-only setup.

Environment notes: sandbox denied pytest temp cleanup and local sockets; authorized
test-owned temp directories and loopback execution resolve those restrictions.
Docker/browser/process interruption stopped initial runs; user restarted Docker.
Some combined full-suite attempts stalled in PDF API execution; report them as
incomplete and run the constituent suites separately. Browser setup initially
omitted the exact-Origin frontend allowlist (403 before generation); corrected.
A Russian dropdown selector typo interrupted inspection after successful publication.
Rapid controlled checks hit the ordinary request-rate limit; rejected before admission,
not counted as provider failures. These attempts are retained in ignored logs.

Real model: zero calls. Configured `gpt-5.6-luna` has a key but no usable local
tariff/operator bounds; both generation flags are ordinarily false. Do not print
credentials or infer that missing prices mean zero cost. Inherited authorization is
24 physical calls including generators/reviewers/retries, 15 minutes and at most
the smaller of the configured authorized ceiling and USD 1. Minimum check=5,
translation=4, regeneration=2 and refresh=2. Six language combinations × three
checks alone require 90 calls. Entire live matrix remains unexecuted; controlled
latency/calls cannot establish real-provider latency, quality, cost or invoice.

Final-browser discovery: project Edit called asynchronous project selection and
view selection separately; the late draft load forced the view back to Check.
Two regression tests failed before fixing this. The destination now travels with
project selection, and the project list issues one navigation action. Independent
read-only review found no important issue in this fix. The final production build
was `ck0i7GA22vr7lxb7jHrR_`. The final build is
`ldGTQGBMzta_XaJGEqt-o`; affected journeys were repeated below.

Before that frontend-only fix, controlled browser ledger evidence recorded 28
successful checks (three per planned scenario plus one additional RU run), six
regenerations including five sequential saved-result regenerations, 158 physical
calls total, no terminal operation failures. Three checks needed correction (one
scope, one schedule, one mixed-language candidate); one regeneration needed a
cosmetic-variant correction. Reviewed replies and CO prose were inspected in the
expected languages. The initial run-log interruption around a confirmation dialog
did not imply a failed operation; operation-ledger evidence and later UI reads
distinguish those outcomes. Rate-limit rejections occurred before admission.

The exact D1 saved translation succeeded with manual 2.5 h / 175.35 USD and
`3 business days after approval` preserved. Final-build manual estimate refresh
then passed three sequential times against a project changed to 80 EUR/hour,
including reload and cleared AI price rationale. These later operations completed
before the test service interruption; their browser logs are retained. A new owned
test database is used for the remaining checks; no application database is touched.

Two additional browser/review findings were fixed before handoff. Immutable History
owns durable PDF content, but the existing current-revision archive command had no
UI action after manual editing. History now offers RU/EN **Archive current document
edits**, explicitly explaining that initial checks are automatic. It flushes the
existing owned Draft and uses the existing archive API; successful checks still need
no Save/Create/Complete action. Incomplete revisions remain editable and marked.

Independent review caught duplicate archives under different successful keys; a
PostgreSQL regression reproduced this. Under the existing project lock the server
now reuses an identical draft/analysis/exact snapshot. Each key gets a durable
`history_saved` receipt with its request hash and History link, so retries still
return their original result and changed parameters reject. Existing original keys
and old records retain their semantics. No migration is needed. A frontend regression
then reproduced duplicate visible list entries for the reused ID; the list now
filters that ID before prepending. Concurrent new keys, alias-key mismatch, changed
content creating a new immutable snapshot and unchanged older content all pass.
Independent read-only follow-up found no important remaining issue in these fixes.

The final source manifest is ignored at
`output/acceptance-2026-10-16/final-source-manifest.json`, SHA256
`f66d6c2fb43a8f1b05b44fd0edb99fa71560fe6c516a4422188baaf1458a41cb`
(45 changed/new production/frontend component/contract files). No application code
changed after the final affected browser scenarios.


## Final browser and provider statistics

All browser generation used `workflow-v5`, the supported
`workflow_v2=true + llm_workflow=true` runtime, real native schema bridge,
ProviderGateway/ledger/reservations and workers, and a controlled HTTP adapter
advertising `gpt-5.4-nano`. It made **zero external model calls**. Latency below is
persisted operation wall time (includes scheduling/validation), not pure model or
whole browser journey time. Physical calls include generator, reviewer and rejected
candidate/correction calls. The synthetic ledger tariff is not an actual bill.

R1 is the initial controlled fixture: output generation on build
`U75SC-DBYK7T0ZiVCJFQF`, followed by manual refresh on `ck0i7GA22vr7lxb7jHrR_`.
R2 repeats all six interface/request combinations three times on `ck0...`, then
runs the affected archive/commercial/history/late-result scenarios on final
`ldGTQGBMzta_XaJGEqt-o`. One of its three D1 runs preceded the final client-list
fix on `A3czx1RRARVo6u6Kgotn8`; the other two repeated restoration/translation/
archive/PDF on the final build. Later changes concerned project navigation and
History archive/dedup only; generation/preservation schemas and policies were
unchanged. Final full-check publication was rerun three times in the late-result
control after the last backend History change. Do not describe all earlier browser
runs as having used the last frontend bundle.

| Scenario | Version/runtime/model | Runs | First attempt | Corrected | Terminal failures | Invalid published observed | Calls | Operation latency s | External provider cost |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| R1 ordinary language checks | v5 / durable / controlled nano | 19 | 19 | 0 | 0 | 0 | 95 | 0.884–3.073 | known USD 0 (fixture) |
| R1 scope/deadline/mixed controls | v5 / durable / controlled nano | 9 | 6 | 3 | 0 | 0 | 50 | 0.715–3.120 | known USD 0 (fixture) |
| R1 saved regeneration | v5 / durable / controlled nano | 6 | 5 | 1 | 0 | 0 | 13 | 1.175–2.194 | known USD 0 (fixture) |
| R1 D1 translation | v5 / durable / controlled nano | 1 | 1 | 0 | 0 | 0 | 4 | 0.630–0.630 | known USD 0 (fixture) |
| R1 manual USD refresh | v5 / durable / controlled nano | 3 | 3 | 0 | 0 | 0 | 6 | 1.084–2.313 | known USD 0 (fixture) |
| R2 language matrix | v5 / durable / controlled nano | 18 | 18 | 0 | 0 | 0 | 90 | 0.754–3.020 | known USD 0 (fixture) |
| R2 late result / duplicate delivery | v5 / durable / controlled nano | 3 | 3 | 0 | 0 | 0 | 15 | 1.179–2.614 | known USD 0 (fixture) |
| R2 D1 translation | v5 / durable / controlled nano | 3 | 3 | 0 | 0 | 0 | 12 | 1.846–2.743 | known USD 0 (fixture) |
| R2 manual USD refresh | v5 / durable / controlled nano | 3 | 3 | 0 | 0 | 0 | 6 | 1.211–2.452 | known USD 0 (fixture) |
| R2 historical regeneration | v5 / durable / controlled nano | 5 | 5 | 0 | 0 | 0 | 10 | 0.880–1.682 | known USD 0 (fixture) |

Total: **70 successful controlled operations, 66 first-attempt, four corrected,
zero terminal operation failures, zero observed invalid generated publications,
301 physical calls**. The final fixture has 21 successful checks and 21 distinct
automatic History IDs; the initial fixture has 28 and 28. Both have zero identical
same-draft/analysis/snapshot duplicates. Explicit manual revisions account for
additional History entries and are not additional checks. R1 ordinary language
checks include one extra RU successful run interrupted only during selector
inspection. Correction cases ran three times each; injection occurred on the first
run per case (scope, unsupported deadline, mixed sentence), not on every repetition.
One regeneration deliberately offered a thank-you-only variant and was corrected.
All other deterministic negative cases are unit/stage/SQL evidence, not extra live
or browser failures.

Final late-result controls: three of three had server `applied=false`, each entered
History once, retained the newer request after reload, and preserved the full source
URL/email/code. Re-delivery of each original operation added neither calls nor
History. Five sequential regenerations on one saved result after the current project
scope/rate changed all used the historical excluded scope. Three final refreshes
kept 2.5 hours / 175.35 USD against the new 80 EUR/hour project; independent AI
suggestions retained their own EUR binding. The short D1 translation passed three
R2 repetitions (plus the earlier R1 run), including reload and durable archives.

Readiness: RU and EN each ran three repetitions of six individual missing fields
(36 field checks), plus missing currency, combined omissions, marked clipboard
content, optional fields and valid free work. Finalization with empty description,
paid amount and currency rejected three times with all three field names. Cancellation
preserved incomplete edits; confirmed restoration and clean login succeeded. Opening
History/restoring saved data triggered zero new model calls. Original legacy-success
empty-History reproduction is resolved by explicit retirement, not by pretending the
legacy path gained persistence.

## Worker PDFs and qualitative inspection

Five actual ExportWorker jobs completed, all first attempt, 1.316–2.005 seconds
persisted queue-to-finish; five browser downloads succeeded. The renderer and API
export/download path are real. Private object storage is an owned in-memory fixture;
production S3/storage integration and deployment remain separate rollout checks.
There were zero LLM calls for PDF/History. External provider cost is known USD 0;
local infrastructure cost and human effort were not metered.

Inspected all six rendered pages: three one-page English D1 downloads (two reuse
identical immutable content), a two-page Russian free-work document, and a one-page
Spanish incomplete-party document. Four unique downloaded PDF byte contents exist.
English shows 2.50 hours / 175.35 USD / `3 business days after approval` and the
faithful manual translation. Russian shows intentional no-additional-charge wording
and an intact approval block on page two. Spanish visibly marks `Proveedor; Cliente`
as incomplete. Labels, glyphs, wrapping, approval/date blanks, page/footer and content
were legible without clipping. RU pagination leaves an approval-only second page;
this was inspected and is usable. Extracted text assertions also passed. A console
encoding issue in an inspection script was corrected by UTF-8 file reads; it was not
PDF glyph corruption.

Manual inspection and controlled fixtures do not establish real-model translation,
semantic-review accuracy or real-provider reliability. The reviewer’s earlier nine
live regenerations and six PDFs/eleven pages remain separate historical evidence.

## Commands and actual outcomes

Run from `backend/` unless stated; unique temp folders were under the ignored
`.superpowers/acceptance-2026-10-16/` and required local execution permissions.

- `uv run --no-sync pytest tests/unit tests/api tests/architecture -q -o faulthandler_timeout=45 -p no:cacheprovider --basetemp=.../unit-export-final`: 596 passed, 82.93 s.
- `uv run --no-sync pytest tests/integration --require-integration -q -p no:cacheprovider --basetemp=.../pg-export-final`: 80 passed, 1034.02 s. Earlier complete integration run: 80 passed, 404.76 s; timings include environmental scheduling differences.
- `pytest tests/integration/test_acceptance_journey.py ...`: three repeated native gateway/PostgreSQL journeys passed, 45.67 s; original pipeline seven passed, 95.25 s.
- Final archive-content/concurrency/key regression: one passed, six deselected, 8.33 s. Duplicate-server test failed first; client duplicate-list test failed first; both pass after fixes.
- Frontend `node node_modules/vitest/vitest.mjs run --maxWorkers=2 --testTimeout=30000`: 357 passed / 49 files, 48.91 s.
- Frontend `node node_modules/typescript/bin/tsc --noEmit`: passed; `node node_modules/eslint/bin/eslint.js .`: zero errors, one inherited unused `_s` warning; `node node_modules/next/dist/bin/next build`: passed, final build `ldGTQGBMzta_XaJGEqt-o`.
- Backend `ruff check .`, `ruff format --check .`: passed, 279 files formatted in backend scope (API/static checks were also run earlier); `mypy src ../apps/api/src` and `--platform win32`: 201 sources passed.
- `python scripts/export_openapi.py --check ../ci/contracts/openapi.json` and frontend `node scripts/api-types.mjs --check`: passed.
- Root `node ci/scripts/check-gateways.mjs --suite contracts`: 20 passed, 4.90 s. `--suite generation-gateway` and `--suite drafts-gateway`: passed retirement/no-call and saved-data read/edit/reload/dedup/ownership journeys, plus 15 auth and 14 project checks each.
- Four Compose configurations rendered successfully; entrypoint tests three passed. Migration/adoption/restart/ownership/architecture checks are included in the backend/SQL suites. No application database migration ran.
- Browser CLI logs/screenshots/PDFs/SQL statistics are ignored in `output/playwright/` and `output/acceptance-2026-10-16/`. Two early combined all-suite attempts stalled and were stopped; they are incomplete, not passes. Constituent suites above completed.
- `git diff --check`: passed (only line-ending advisories).

## Finding disposition and remaining ownership

| Finding | Disposition | Evidence / limit |
|---|---|---|
| Valid EN/RU/ES CO headings reject; all live full checks blocked | Fixed in controlled final implementation | Server catalog composition, exact artifact regressions, repeated complete publication; real-model rerun blocked |
| Manual amount/currency corruption and stale rationale | Fixed | Atomic/provenance/ownership tests, repeated PostgreSQL merges, two browser groups of three refreshes, Copy/PDF |
| Short D1 translation failure | Validator defect fixed; bad candidates still rejected | Actual attempts 1/3 stale-price additions rightly rejected; attempt 2 now accepted; three final-fixture translations and PDFs |
| Working/calendar days, dates and conditional promises | Fixed within bounded validation policy | Positive/negative localized stage/SQL tests; final D1 business-day wording; semantic accuracy on real models unverified |
| Scope, unauthorized commitments, foreign sentences, cosmetic variants, uncertain review | Existing ANY-688 work integrated and verified deterministically | Native gateway/ledger tests, exhausted budgets and corrections, historical regeneration; real judge quality blocked |
| Missing-data guidance / usable edited CO | Fixed | RU/EN fields, optional/free controls, specific finalization errors, marked preview/Copy/PDF; existing archive action exposed for edits |
| Supported successful legacy execution without History | Retired with upgrade response | 503/426 controls, zero provider fallback, supported durable runtime automatically archives every check |
| Project Edit navigation reset | Fixed additional browser finding | Two failing regressions, final project mutation/refresh browser path |
| Duplicate current-revision History / duplicate visible list | Fixed additional review/browser finding | Failing tests, exact-snapshot reuse with per-key receipts, concurrency/new-content/immutability and browser reuse |
| Paid real-provider full journey | Blocked | Missing valid local pricing bounds; inherited 24-call/15-min/USD ceiling cannot authorize an unlimited matrix |
| Production migration, storage, coordinated rollout and business acceptance | Not executed | Operator-owned steps above; no commits/push/PR/status changes or real-data writes |

Do not mark all tickets accepted from these controlled results. Final acceptance is
bounded by the exact version, supported runtime, synthetic provider and owned storage
fixture above. The full real-provider language/translation/schedule/regeneration/
refresh matrix remains unexecuted; real cost, latency and model quality are unknown.


## Final preservation and elapsed-time handoff

All work remains uncommitted on `codex/any-688-output-validation`, base/HEAD
`4450ecacc89f7fd67fc62cdaf3bdc740dc4988cb`, without upstream. No commit, push,
merge, PR, Linear status mutation or application DB migration occurred. Ignored
AGENT.md and WORKLOG.md were appended; existing journal text was retained.

Unrelated preservation hashes match the pre-edit inventory:

- `.gitignore`: `8FA457477F2D6A96F456FDDD3D9D94D7922A83640BC143BB466FF33F71E24871`.
- `docs/design/project-draft-ai-workflow.md`: `3594E978F9BAAF391B9BE6AEF500D1B97B611C9F45E1C3ED321B0DF0DC4873CF`.
- `docs/design/project-draft-ai-workflow-v1-old.md`: `41E23568B969D6E8AF5852929BCA4ED2BAFFB2A5148679B12771A97E5D60074C`.

The original ANY-688 implementation was integrated, not reset. Review/design and
ignored evidence files remain available. CLI artifacts created by this task moved
into ignored output; no application file cleanup was performed. Owned API/frontend
and the named browser session were stopped. Four leftover disposable containers
from this task were removed only after immutable IDs, ownership labels, creation
intervals and synthetic database names were verified. Downloaded PDFs, snapshots,
ledger statistics and source manifest remain under ignored output.

Recorded machine wall-clock interval: **2026-10-15 22:09:43 UTC through
2026-10-16 09:48:19 UTC**, 41,916 seconds / 11 h 38 m 36 s (01:09:43 through
12:48:19 MSK on 16 October). This spans stopped-session/user interruptions,
Docker restart, tool waits and environmental scheduling; it is not active CPU time
or continuous engineering effort. Initial discovery before the start and final
bookkeeping after this endpoint are excluded. Human labor and billable hours are
unknown and must not be inferred from the interval.


## Publication follow-up

After this verification, the user explicitly authorized a GitHub push and PR.
The publication branch is `codex/any-688-acceptance-corrections`, based on
`origin/main` (`f00e1014c376cba9e5dc65e73421a98c3aa3c37e`). Its starting tree is
identical to the original committed base `4450ecacc89f7fd67fc62cdaf3bdc740dc4988cb`.
All verified working files were retained in the existing checkout; the original
`codex/any-688-output-validation` branch/history was not rewritten. This satisfies
the repository's main-ancestor/no-merge CI requirement without rebasing existing
commits. The 45-file source manifest still matches exactly; application behavior
and recorded verification results are unchanged. The branch/HEAD/uncommitted
statements earlier in this record describe the verification endpoint before this
subsequent publication request. Unrelated `.gitignore` edits and local design files
remain outside the commit. Ignored journals and local evidence are retained locally.
No merge, deployment, database migration or Linear status change is authorized.
