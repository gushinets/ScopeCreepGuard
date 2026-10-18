# Scope assessment and marketing metrics completion

Date: 2026-10-18, Europe/Moscow. Work is local and uncommitted.

Acceptance is qualified: targeted repairs and controlled journeys pass, but an
initial concurrent admission500 remains unresolved and no clean broad backend
run completed. The rebuilt local application is running with preserved data.

## Baseline and changes

Branch `codex/scope-assessment-and-metrics-completion` starts at fetched origin/main
`fe0e68229efbd586c5ea20cd7b488d931c699b5e`. Original clean local main was
`af0ffdc34f75fdf852a69dccdbd19e158852fcc8`; its nine documentation files remain
preserved, untracked on this branch. Main was not moved. No worktree, stash,
reset, commit, push, PR, remote merge or Linear mutation was performed.

Patch comparisons (`git cherry origin/main <branch>`) establish that all commits
on the three requested feature branches are integrated. Original commits
2714cd6/37df435 correspond to 74a9c73/29c67f4; 9c07515/9c01aa4 correspond to
bbadc7d/3084c10; f1cd5af/16118a8 correspond to 80c2e74/fe0e682. No cherry-picks
or whole-branch merges were needed. The implementation plan was recorded before
code edits in `plans/2026-10-18-scope-assessment-metrics-completion.md`.

## Assessment trace

Historical reference is `29c67f4580bea8a7d58530beaeea2abb537af1a9`, the parent of
`336571752f3811ed8af084bfa6e9e000996bc42c`. Inspected its result panel and prompts,
then traced current frontend types/schema/store, API AnalysisSnapshot, backend
AnalysisStage, prompts, normalization, serialization, worker publication and
history snapshots. Relevant installed Next.js server/client component and
`use client` guides were read before frontend edits.

| Element | Historical/source evidence | Integrated behavior |
| --- | --- | --- |
| Verdict, confidence, summary | Historical VerdictBanner; AnalysisStage and AnalysisResult | Already restored in baseline; reused in live result and now History detail |
| Requested change relative to scope | Saved request, analysis summary/reasoning, frozen project scope | Request and scope comparison visible without generating a document |
| Inside/outside/borderline explanation | Historical result.reasoning and classification prompt | Original assessment snapshot remains authoritative |
| Supporting quotations | Historical result.citations; verbatim-source prompt rule | Quotations rendered verbatim, including original source language |
| Additional work | hasAdditionalWork; historical ChangeOrder estimates | Existing flag and preliminary numeric estimates rendered immediately |
| Preliminary effort/cost | Historical changeOrder.estimatedHours/additionalCost/currency; current result.estimate | Current estimate first, historical original ChangeOrder numeric fallback; never editable agreement values |
| Practical recommendation | Historical result.suggestion; existing analysis prompt/schema | Existing optional recommendation rendered |

The fetched baseline already repairs the main result panel. Browser inspection
found a remaining rendering gap in `PersistentHistoryView`: only reasoning/reply
were shown despite the complete archived analysis being present. This change
reuses `ScopeAssessment` there. Its regression failed in both locales before the
repair and passed afterward. No generation schema, mandatory field, migration,
automatic agreement, old reply rewrite or historical snapshot mutation was added.
Historical agreement description/schedule/rationale/disclaimer remain client
material, not an interface-language assessment. Zero/missing preliminary amounts
were also verified without changing existing behavior.

## Language and commercial authority

`backend/src/scope_guard/integrations/llm/detection.py` already contains the correct
integrated priority: valid explicit override, supported leading request candidate
regardless of confidence/status, then supported interface locale or English only
without usable evidence. Exact typo request `build a new page for our custmores`
produces en / 0.4078 / uncertain and selects English in Russian UI. Diagnostics
remain internal and nonblocking. Provider messages target interface locale for
analysis and selected client language for replies/Change Order. Automatic choices
are recomputed on a new request; an explicit choice is preserved for the same
request and cleared when its request changes.

Controlled real-path tests verify Russian UI/English request, English UI/Russian
request, Spanish with both interface locales, explicit Spanish override and
language-neutral URL/emoji fallback. Saved 12 hours/EUR975/schedule override old
AI 8 hours/USD240 proposals in actual regeneration payloads; cleared fields and
free-work selection remain authoritative. Original analysis and saved History
hashes remain unchanged through these edits. Agreement preparation is explicit;
finalization is a separate source fact. A prepared draft alone is not a finalized CO.

## Actual collection and metrics architecture

Authentication resolves users.id. Registration atomically creates the unique
profiles.user_id relation, preferences/revision and profile.created event. Project
ownership is checked against the authenticated user and matching profile. No
client-supplied profile ID is trusted. Signed browser identity and product_sessions
track trusted visible user interaction, with shared tabs and 30-minute inactivity;
login/polling alone do not activate the product. No session duration KPI exists.

API -> services/WorkflowUnitOfWork -> projects, drafts/revisions, analysis_runs,
history_entries, finalized change_orders, activity_events and LLM ledger.
SqlAlchemyUnitOfWork commits T1, closes its session, then synchronously invokes
MetricsService through a separate new_metrics_uow T2. T2 acquires the global
advisory lock before one READ COMMITTED source projection, recalculates retained
UTC history and atomically upserts marketing_metrics with a freshness guard.
Its UoW has no recursive callback. T2 errors are logged after T1 and cannot undo
saved results. Supported read/reconcile or the next dirty action recovers from
committed sources; no new scheduler, worker, analytics platform or database was
introduced. Direct table reads can be stale until such reconciliation.

Events use immutable source/deduplication keys and content-aware conflict checks.
Durable command receipts and project/profile locking prevent duplicated results
and lost updates. Recalculation derives values from facts rather than increments.
The existing migrations/mappings and ownership constraints were inspected and
exercised on disposable PostgreSQL. No new migration is required by this change.

The second repair excludes agreement preparation from aggregate product operation
success/failure/duration totals. The agreed set is exactly check, regeneration,
translation and estimate. A new unit regression observed operations_failed=1 for
an agreement-only failure before the fix and 0 afterward. Preparation and diagnostic
ledger/calls remain retained; confirmed AI accounting still includes them.

Definitions were recorded before this repair in the plan. Authority is
`../design/profile-behavior-marketing-metrics.md`, especially resolved section 11,
and `marketing-metrics.md`: meaningful activity is a successful explicitly saved
baseline check or finalized CO; first saved check in [registration,registration+7d)
activates, with only mature registrations in that rate's population. DAU is unique
profiles/day, MAU current+29 prior UTC days; PQL requires >=3 checks and >=1 finalized
CO in that window. D7/D30 retention uses exact calendar return day. Feature adoption
intersects same-day function users with DAU. Durations include queue/retries, starts
use admission day, terminal outcomes use completion day. All intervals are half-open.
Unknown values and zero-denominator rates are NULL; the current day is partial.
AI calls/tokens/estimated costs/validation were explicitly approved in section 11;
physical-call start UTC date owns late accounting, retries are semantic>1 OR
transport>1 once per call, missing usage/cost produces NULL and unknown counters.
PDF KPIs, acceptance/payment, session duration, admin and inferred traits are absent
and outside the agreed final table; they are not described as collected metrics.

## Verification evidence and limits

All generated responses were controlled fixtures at the provider adapter boundary,
using real admission, gateway, validation, worker, publication and persistence.
No paid/live AI call was made. This verifies integration and payload authority,
not live-model linguistic or assessment quality.

Ignored evidence is under `../../output/scope-assessment-metrics-completion/`
and `../../output/playwright/scope-assessment-metrics-completion/`. The original
isolated runtime's database was lost when the Docker VM stopped; its source
snapshots, independent comparisons, provider payloads and receipts remain saved.
A separate final browser runtime uses bounded containers and a fresh test database.
No original application user was used as a disposable fixture.

- Full frontend: **401 tests / 55 files plus 20 Python HTTP contracts passed**, using
  the existing disposable compatibility harness with two local workers.
- New assessment/History component checks: RED two History tests, then **14 passed**.
- Focused backend language/commercial/formula checks: **43 passed** initially;
  agreement exclusion then RED one failure, GREEN **13 formula tests passed**.
- Backend unit/API: **675 passed, six temp-directory fixture errors**; all six
  passed in a fresh owned workspace temporary directory. This is not a clean
  single full-suite run. Initial restricted run also had three technical-process
  failures and the same six temp errors; retained in backend.log.
- Focused PostgreSQL: **34 tests passed**, then teardown failed with WinError1455
  (paging file too small). Original incorrectly rooted run failed before migration
  with the documented backend-working-directory guard. A later detached retry
  aborted after 13 tests, exit -1073740791. Neither full run is marked clean PASS.
- Later broad Windows run interrupted after a failure near 84%; it has no terminal
  report. Disposable Linux broad run showed two failures before Docker disconnected
  with unexpected EOF, exit125; details were not emitted before interruption.
  These runs remain incomplete/failed evidence, not successes hidden by retries.
- Full frontend image and matching API/worker images built successfully. Ruff and
  diff checks passed. Final lint/TypeScript/runtime status is recorded below.

One initial concurrent same-key HTTP admission produced 500 for one caller and
202 for the other, with one successful persisted result. The original exception
was not captured by the sanitized log. Host memory pressure is a possible cause,
not a proven diagnosis. A fresh API cold-start repeat returned two202 responses
with the same operation Location, then three terminal replays returned the same
result. This does not erase the original failure or establish its cause.

The initial SQL oracle used PostgreSQL float8 percentile_cont and Python decimal
rounding. Two duration columns differed by 0.001ms. The corrected independent SQL
interpolates numeric source observations and casts to declared database scales;
**all 89 columns match**. Original discrepancies are retained in live-reference.json;
correct comparisons in live-reference-final.json. No product precision was changed.
Controlled multi-day source fixtures in another disposable database reconciled
**44 rows / 3916 comparisons**, including D7/D30, mature/late/boundary activation,
MAU expiry, PQL, exclusion and duplicate archives, with no SQL differences.

Runtime verification, scenario table and complete per-column comparison follow.

## Scenario acceptance

PASS identifies the stated test layer, not live-model quality. The initial concurrency failure remains a material unresolved defect. Browser tests used isolated PostgreSQL and synthetic accounts only.

| Scenario | Expected UI and database outcome | Actual outcome | PASS / FAIL / BLOCKED | Evidence |
| --- | --- | --- | --- | --- |
| Register/login/profile | One profile per technical user; login has no activation | Original register/login receipts agree; final browser has two users/two profiles | PASS | [01-register.json](../../output/scope-assessment-metrics-completion/01-register.json) |
| Project only | No meaningful activity until saved check or finalized CO | Initial project snapshot DAU 0 | PASS | [20-final-browser-registration-project.json](../../output/scope-assessment-metrics-completion/20-final-browser-registration-project.json) |
| Russian UI + exact English typo | Russian full assessment; English reply; no automatic agreement | Final image: verdict/confidence/request/reason/quote/8h/$240/recommendation; English reply | PASS | [../playwright/scope-assessment-metrics-completion/final-ru-assessment-en-typo.txt](../../output/scope-assessment-metrics-completion/../playwright/scope-assessment-metrics-completion/final-ru-assessment-en-typo.txt) |
| English UI + Russian request | English assessment; Russian reply | Second browser identity has both, separately persisted | PASS | [../playwright/scope-assessment-metrics-completion/final-second-user.txt](../../output/scope-assessment-metrics-completion/../playwright/scope-assessment-metrics-completion/final-second-user.txt) |
| Spanish request + either UI | es client target independent of en/ru assessment | Both API-worker language cases passed; actual provider payloads checked | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Explicit Spanish override | Translate client material, preserve Russian assessment | Browser override and HTTP analysis equality passed | PASS | [../playwright/scope-assessment-metrics-completion/ru-assessment-es-override.txt](../../output/scope-assessment-metrics-completion/../playwright/scope-assessment-metrics-completion/ru-assessment-es-override.txt) |
| No usable language evidence | Documented interface fallback; nonblocking | URL/emoji-only request selected ru fallback | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Changed request / stale automatic language | New candidate replaces obsolete automatic selection; explicit override retained | Focused scope-language regression tests pass | PASS | [focused-backend-final.log](../../output/scope-assessment-metrics-completion/focused-backend-final.log) |
| Explicit agreement / edited terms | Prepare only on action; selected material language; current saved 12h/975EUR/schedule governs regeneration | Browser saved agreement and selected reply regeneration; provider payload has current authority | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Free work / cleared values | No revival of old AI price/hours/schedule; preliminary assessment independent | HTTP real persistence and provider-payload assertions pass | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Immutable reopened history | Complete original assessment retained alongside archived material | Final built history renders confidence, evidence, original estimate and recommendation; snapshot hash unchanged by commercial edits | PASS | [../playwright/scope-assessment-metrics-completion/final-history.png](../../output/scope-assessment-metrics-completion/../playwright/scope-assessment-metrics-completion/final-history.png) |
| Browser double click | One result, one explicit saved check | Final image dblclick: one analysis/history row | PASS | [21-final-browser-double-click-history.json](../../output/scope-assessment-metrics-completion/21-final-browser-double-click-history.json) |
| Concurrent same-key admission | Both callers get one accepted action without server error | Initial one500/one202 with one persisted success; later cold2x202 and terminal3x200 same result. Cause unresolved | FAIL | [journey-r2.log](../../output/scope-assessment-metrics-completion/journey-r2.log) |
| New intentional action | New key can count separately with same text | Independent saved check added | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Two tabs / identity separation | Same browser session; no duplicate profiles/actions; no cross-account visibility | Final two tabs: two total users/profiles/projects/checks/histories/sessions; DAU=MAU=2; ownership HTTP404 | PASS | [22-final-browser-two-users.json](../../output/scope-assessment-metrics-completion/22-final-browser-two-users.json) |
| Failed operation | Failure counted once; no successful saved action | Controlled adapter failure reached real worker failed state and metrics | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Metrics T2 failure after product commit | Successful result remains saved and retrievable | Test-only final-table trigger rejected T2; product/source success persisted | PASS | [http-journey.json](../../output/scope-assessment-metrics-completion/http-journey.json) |
| Recovery / repeated recalculation | Supported read repairs derived table; repeat cannot double count | Fault removed, supported service reconciled; stable figures and independent SQL match | PASS | [live-reference-final.json](../../output/scope-assessment-metrics-completion/live-reference-final.json) |
| Controlled multi-day windows | UTC boundaries/activation/PQL/retention correct | 44 daily rows / 3916 comparisons; D7/D30 returned1; DAU3/MAU4/PQL1 fixture assertions | PASS | [windows-result.json](../../output/scope-assessment-metrics-completion/windows-result.json) |
| Full backend validation | One clean broad backend and integration run | Unit tests split across successful runs; PG34 passed then resource failure in teardown; later runs interrupted | BLOCKED | [integration-r2.log](../../output/scope-assessment-metrics-completion/integration-r2.log) |
| Live-model quality | Real provider semantic/language quality | No paid calls authorized or made; controlled adapter only | BLOCKED | [provider-payloads.jsonl](../../output/scope-assessment-metrics-completion/provider-payloads.jsonl) |
| Existing local runtime/data | Rebuilt matching API/worker/frontend; no migration/product rewrites | Healthy API/frontend/PG; worker running;0007 unchanged; four product fingerprints identical | PASS | [application-final-services.txt](../../output/scope-assessment-metrics-completion/application-final-services.txt) |

## Independent per-column reconciliation

Frozen original full HTTP/browser journey, report date 2026-10-18. The independent [reference SQL](../../output/scope-assessment-metrics-completion/reference.sql) reads raw tables and never calls the production calculator. [Full values](../../output/scope-assessment-metrics-completion/live-reference-final.json); final-image second-user run separately matches all89 columns in [final-browser-reference.json](../../output/scope-assessment-metrics-completion/final-browser-reference.json).

`calculated_at` and `data_through` are metadata, deliberately taken from the row to reproduce its observation boundary; equality is not independent proof of their wall-clock correctness. The service guarantees a post-lock snapshot and monotonic cutoff; current-day partial flags and cutoff <= calculation time were inspected. `report_date` is the query boundary and definition_version is a contractual literal. Other columns are independently calculated from source observations. This fixture has current durable operations and no legacy sources; legacy quality flags are covered by existing formula tests, not claimed as independently reconciled here.

| Metric / final column | Source | Calculation | Expected value | Actual value | Status |
| --- | --- | --- | --- | --- | --- |
| `report_date` | UTC boundary | Selected UTC calendar date | 2026-10-18 | 2026-10-18 | METADATA |
| `calculated_at` | marketing_metrics metadata | Recorded recompute instant; source cutoff <= calculation time | 2026-10-18 10:35:43.138440+00:00 | 2026-10-18 10:35:43.138440+00:00 | METADATA |
| `data_through` | marketing_metrics metadata | Snapshot cutoff used consistently by all reference queries | 2026-10-18 10:35:43.126721+00:00 | 2026-10-18 10:35:43.126721+00:00 | METADATA |
| `definition_version` | agreed definitions | Literal version 1 | 1 | 1 | PASS |
| `is_partial` | provider_calls / cutoff | OR of current incomplete day and observed missing accounting flags | True | True | PASS |
| `quality_notes` | provider_calls / cutoff | Sorted applicable incomplete-day/unknown-usage/cost notes (fixture has no legacy records) | ["ai_cached_or_reasoning_usage_incomplete", "ai_estimated_cost_incomplete", "ai_input_output_usage_incomplete", "report_day_incomplete"] | ["ai_cached_or_reasoning_usage_incomplete", "ai_estimated_cost_incomplete", "ai_input_output_usage_incomplete", "report_day_incomplete"] | PASS |
| `ai_calls` | provider_calls + operation owner profile | Physical calls started in UTC day | 36 | 36 | PASS |
| `ai_retries` | provider_calls | Calls semantic_attempt>1 OR transport_attempt>1, once | 0 | 0 | PASS |
| `input_tokens` | provider_calls | SUM(input_tokens) on call-start day; NULL if any missing; zero if no calls | NULL | NULL | PASS |
| `output_tokens` | provider_calls | SUM(output_tokens) on call-start day; NULL if any missing; zero if no calls | NULL | NULL | PASS |
| `cached_tokens` | provider_calls | SUM(cached_tokens) on call-start day; NULL if any missing; zero if no calls | NULL | NULL | PASS |
| `reasoning_tokens` | provider_calls | SUM(reasoning_tokens) on call-start day; NULL if any missing; zero if no calls | NULL | NULL | PASS |
| `ai_estimated_cost_usd` | provider_calls | SUM observed USD cost; NULL if any unknown; zero if no calls | NULL | NULL | PASS |
| `ai_cost_unknown_calls` | provider_calls | Day calls with missing estimated_cost | 2 | 2 | PASS |
| `ai_usage_unknown_calls` | provider_calls | Day calls missing input or output tokens | 2 | 2 | PASS |
| `validation_accepted` | provider_calls | Count matching accepted/rejected validation on call-start day | 34 | 34 | PASS |
| `validation_rejected` | provider_calls | Count matching accepted/rejected validation on call-start day | 0 | 0 | PASS |
| `validation_rejection_percent` | provider_calls | 100*rejected/(accepted+rejected); NULL if zero | 0.0000 | 0.0000 | PASS |
| `registered_profiles` | profiles | Non-excluded profiles registered before cutoff | 2 | 2 | PASS |
| `new_profiles` | profiles | Registrations in UTC day before cutoff | 2 | 2 | PASS |
| `dau` | explicit successful checks + finalized CO | Distinct non-excluded profiles active in UTC day | 2 | 2 | PASS |
| `mau` | explicit successful checks + finalized CO | Distinct active profiles in current + preceding29 UTC days | 2 | 2 | PASS |
| `activation_eligible_profiles` | profiles | Registration +7days <= cutoff | 0 | 0 | PASS |
| `activated_profiles` | profiles + first saved check | Eligible profile first check in [registration,registration+7days) | 0 | 0 | PASS |
| `ttv_sample_size` | profiles + first saved check | Count profiles with first saved check since registration before cutoff | 2 | 2 | PASS |
| `pql_profiles` | saved checks + finalized CO | >=3 checks and >=1 finalized CO in rolling30 UTC days | 1 | 1 | PASS |
| `retention_d7_base` | profiles + first check + product activity | Timely-activation cohort first-check UTC date = report date -7 | 0 | 0 | PASS |
| `retention_d7_returned` | profiles + first check + product activity | Profiles in D7 cohort with product activity on report date | 0 | 0 | PASS |
| `retention_d30_base` | profiles + first check + product activity | Timely-activation cohort first-check UTC date = report date -30 | 0 | 0 | PASS |
| `retention_d30_returned` | profiles + first check + product activity | Profiles in D30 cohort with product activity on report date | 0 | 0 | PASS |
| `analysis_users` | saved checks / finalized CO / successful operation | Distinct day feature profiles intersected with DAU | 2 | 2 | PASS |
| `regeneration_users` | saved checks / finalized CO / successful operation | Distinct day feature profiles intersected with DAU | 1 | 1 | PASS |
| `translation_users` | saved checks / finalized CO / successful operation | Distinct day feature profiles intersected with DAU | 1 | 1 | PASS |
| `change_order_users` | saved checks / finalized CO / successful operation | Distinct day feature profiles intersected with DAU | 1 | 1 | PASS |
| `change_orders_created` | change_orders | Count finalized in UTC day, even subsequently voided | 1 | 1 | PASS |
| `change_orders_voided` | change_orders | Count voided in UTC day and finalized before cutoff | 0 | 0 | PASS |
| `verdict_correct` | evaluation_cases + saved checks | Count matching feedback attached to a saved check completed in day | 0 | 0 | PASS |
| `verdict_wrong` | evaluation_cases + saved checks | Count matching feedback attached to a saved check completed in day | 0 | 0 | PASS |
| `verdict_debatable` | evaluation_cases + saved checks | Count matching feedback attached to a saved check completed in day | 0 | 0 | PASS |
| `verdict_evaluated_checks` | evaluation_cases + saved checks | Count day checks with correct/wrong/debatable feedback | 0 | 0 | PASS |
| `operations_succeeded` | llm_operations (four agreed kinds) | Count matching terminal status on finished_at UTC day | 12 | 12 | PASS |
| `operations_failed` | llm_operations (four agreed kinds) | Count matching terminal status on finished_at UTC day | 1 | 1 | PASS |
| `operations_cancelled` | llm_operations (four agreed kinds) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `operation_duration_sample_size` | llm_operations (four agreed kinds) | Terminal-day operations with valid nonnegative created-to-finished duration | 13 | 13 | PASS |
| `check_started` | llm_operations (named kind) | Admissions created in UTC day | 10 | 10 | PASS |
| `check_succeeded` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 9 | 9 | PASS |
| `check_failed` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 1 | 1 | PASS |
| `check_cancelled` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `check_duration_sample_size` | llm_operations (named kind) | Terminal-day operations with valid nonnegative created-to-finished duration | 10 | 10 | PASS |
| `regeneration_started` | llm_operations (named kind) | Admissions created in UTC day | 2 | 2 | PASS |
| `regeneration_succeeded` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 2 | 2 | PASS |
| `regeneration_failed` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `regeneration_cancelled` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `regeneration_duration_sample_size` | llm_operations (named kind) | Terminal-day operations with valid nonnegative created-to-finished duration | 2 | 2 | PASS |
| `translation_started` | llm_operations (named kind) | Admissions created in UTC day | 1 | 1 | PASS |
| `translation_succeeded` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 1 | 1 | PASS |
| `translation_failed` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `translation_cancelled` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `translation_duration_sample_size` | llm_operations (named kind) | Terminal-day operations with valid nonnegative created-to-finished duration | 1 | 1 | PASS |
| `estimate_started` | llm_operations (named kind) | Admissions created in UTC day | 0 | 0 | PASS |
| `estimate_succeeded` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `estimate_failed` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `estimate_cancelled` | llm_operations (named kind) | Count matching terminal status on finished_at UTC day | 0 | 0 | PASS |
| `estimate_duration_sample_size` | llm_operations (named kind) | Terminal-day operations with valid nonnegative created-to-finished duration | 0 | 0 | PASS |
| `stickiness_percent` | DAU / MAU sources | 100*DAU/MAU; NULL on zero denominator | 100.0000 | 100.0000 | PASS |
| `activation_rate_percent` | activation sources | 100*activated/eligible; NULL on zero denominator | NULL | NULL | PASS |
| `retention_d7_percent` | profiles + first check + product activity | 100*D7 returned/base; NULL for zero base or incomplete report day | NULL | NULL | PASS |
| `retention_d30_percent` | profiles + first check + product activity | 100*D30 returned/base; NULL for zero base or incomplete report day | NULL | NULL | PASS |
| `analysis_adoption_percent` | feature success + day product activity | 100*feature_users/DAU; NULL if DAU zero | 100.0000 | 100.0000 | PASS |
| `regeneration_adoption_percent` | feature success + day product activity | 100*feature_users/DAU; NULL if DAU zero | 50.0000 | 50.0000 | PASS |
| `translation_adoption_percent` | feature success + day product activity | 100*feature_users/DAU; NULL if DAU zero | 50.0000 | 50.0000 | PASS |
| `change_order_adoption_percent` | feature success + day product activity | 100*feature_users/DAU; NULL if DAU zero | 50.0000 | 50.0000 | PASS |
| `verdict_feedback_percent` | evaluation_cases + saved checks | 100*evaluated/day checks; NULL when zero checks | 0.0000 | 0.0000 | PASS |
| `operation_success_percent` | llm_operations (four agreed kinds) | 100*succeeded/(succeeded+failed+cancelled) terminal day; NULL if zero | 92.3077 | 92.3077 | PASS |
| `check_success_percent` | llm_operations (named kind) | 100*succeeded/(succeeded+failed+cancelled) terminal day; NULL if zero | 90.0000 | 90.0000 | PASS |
| `regeneration_success_percent` | llm_operations (named kind) | 100*succeeded/(succeeded+failed+cancelled) terminal day; NULL if zero | 100.0000 | 100.0000 | PASS |
| `translation_success_percent` | llm_operations (named kind) | 100*succeeded/(succeeded+failed+cancelled) terminal day; NULL if zero | 100.0000 | 100.0000 | PASS |
| `estimate_success_percent` | llm_operations (named kind) | 100*succeeded/(succeeded+failed+cancelled) terminal day; NULL if zero | NULL | NULL | PASS |
| `time_to_value_median_seconds` | profiles + first saved check | Numeric interpolated median(first check - registration) seconds | 1129.155 | 1129.155 | PASS |
| `operation_duration_median_ms` | llm_operations (four agreed kinds) | Original duration ms numeric interpolated median; NULL without samples | 3293.043 | 3293.043 | PASS |
| `operation_duration_p95_ms` | llm_operations (four agreed kinds) | Original duration ms numeric interpolated P95; NULL without samples | 4275.616 | 4275.616 | PASS |
| `check_duration_median_ms` | llm_operations (named kind) | Original duration ms numeric interpolated median; NULL without samples | 3807.137 | 3807.137 | PASS |
| `check_duration_p95_ms` | llm_operations (named kind) | Original duration ms numeric interpolated P95; NULL without samples | 4354.327 | 4354.327 | PASS |
| `regeneration_duration_median_ms` | llm_operations (named kind) | Original duration ms numeric interpolated median; NULL without samples | 1925.527 | 1925.527 | PASS |
| `regeneration_duration_p95_ms` | llm_operations (named kind) | Original duration ms numeric interpolated P95; NULL without samples | 2166.363 | 2166.363 | PASS |
| `translation_duration_median_ms` | llm_operations (named kind) | Original duration ms numeric interpolated median; NULL without samples | 2257.652 | 2257.652 | PASS |
| `translation_duration_p95_ms` | llm_operations (named kind) | Original duration ms numeric interpolated P95; NULL without samples | 2257.652 | 2257.652 | PASS |
| `estimate_duration_median_ms` | llm_operations (named kind) | Original duration ms numeric interpolated median; NULL without samples | NULL | NULL | PASS |
| `estimate_duration_p95_ms` | llm_operations (named kind) | Original duration ms numeric interpolated P95; NULL without samples | NULL | NULL | PASS |

## Final runtime, review and handoff

The actual local application is running at http://localhost:3000 from the rebuilt
completion images, with API at8000. Frontend/API/PostgreSQL are healthy; the
existing LLM worker is running. Backend and worker import the same repaired
marketing module (SHA256 `25425b83fa6eca1c95e7cf0aab56ffe83c4e821d4aa8f9dbf15a1a7a9a3017fd`).
Image IDs recorded in application-final-services.txt:

- app: `e470d62ea457032ddbe8bfd259f25f1d3fb6df5437dd05a07ee08a7c57ce2b32`
- API: `98ad245a52e0f92e829c1d8aa9170dc81005bf6065adb1343df2007adfb9ac67`
- worker: `03f1c4c78ad802aeee9cf78fc3352710753adaa28c3c46cf7f9bd8c9ce4f5836`

All operations were terminal before replacement. Existing schema already was
`0007_nonblocking_llm`; no new migration was created or applied to the local
application database. Supported MetricsService.read refreshed derived records
only. Before/after exact record fingerprints match for history_entries34,
analysis_runs6, drafts3 and change_orders0. Existing operations remain19succeeded,
2failed; physical-call ledger38. No test accounts were inserted in this database.
The final isolated test containers are stopped and their separate database retained.

Final focused backend run passes44 tests (scope assessment/language, commercial
authority and marketing formulas), exit0 in focused-backend-final.log. Final
changed-file ESLint and TypeScript pass (exit0). The first Windows TypeScript
process aborted with -1073740791; a bounded container attempt could not resolve
Windows pnpm symlinks. A subsequent serial Windows check with512MB heap finished
cleanly. No check settings or acceptance assertions were weakened. Existing Next
configuration ignores build type errors, so the independent TypeScript pass matters.
Read-only independent review found no actionable issues in the two production
changes, specifically frozen history and the four-kind aggregate/independent AI
accounting. This review did not resolve the initial concurrent500 or certify
unchanged baseline/live-model behavior.

Remaining limitations: the initial same-key500 is a reproducible observed admission
failure without a captured underlying exception; later repeats passed but do not
prove a fix. A clean whole backend/integration run remains blocked by host failures
and incomplete failure diagnostics; the complete log history is retained. The
frontend full suite, focused backend tests, controlled PostgreSQL scenarios and
independent SQL evidence pass at their stated layers. Live-provider semantics and
quality are unverified, with no paid AI calls made. No historical replies or saved
assessment records were silently rewritten. No commit, push or PR was created.

![Complete archived assessment in the final image](../../output/playwright/scope-assessment-metrics-completion/final-history.png)

![Second identity: English assessment and Russian reply](../../output/playwright/scope-assessment-metrics-completion/final-second-user.png)
