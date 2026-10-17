# Profile, behavior and marketing metrics verification

Historical verification for the implementation version identified below. The
[2026-10-17 follow-up](2026-10-17-profile-observation-verification.md) supersedes
its per-input observation delivery policy and records the bounded observer tests;
the original measured results and source manifest remain unchanged.

Implementation and verification complete; changes remain uncommitted for review.
No push, PR, merge, deployment, Linear mutation or application database migration
was performed. ANY-689 remains a discovery/data-clarification ticket.

## Version and preserved state

- Branch: `codex/profile-behavior-marketing-metrics`.
- Approved fetched base/unchanged HEAD: `3fe66f174807286f8d3e748b63fe89dbb91351ec`
  (`origin/main` after PR24 merged at 2026-10-16 11:03:37 UTC).
- Used the current checkout, without a worktree or history rewrite. Previous local
  `8450bbe` remains on its original branch and was not inherited.
- Exact uncommitted application/test version: **602 files**, manifest SHA-256
  `c6ce8b9e21fe7576e63878fb9edf260b2ea7e3a8732d96e251f4536c9d2b1847`.
  [Manifest](../../output/profile-metrics/source-manifest.json) contains individual
  hashes and the authoritative design hash. Recomputing after all tests matched.
- Final Next.js16.3.0 production build: `nvgzQCwgsWo1r-YwFHrge`.
- Final API/worker fixture started **2026-10-17 00:32:42 UTC** after review fixes.
  All three journeys were repeated against this restarted final-code fixture.
- Preserved the unrelated `.gitignore` change and both unrelated untracked workflow
  designs byte-for-byte, verified against their initial SHA-256 hashes. Preserved
  the authoritative untracked design and ignored local configuration/handoffs.

## Implementation and event coverage

Reused `users`, projects, drafts/revisions, analysis runs, immutable history,
change orders/revisions, evaluation cases, `activity_events`, and the existing
LLM operation/step/provider-call ledger. Added exactly `profiles`,
`profile_preferences`, `profile_revisions`, `product_sessions` and the wide,
typed `marketing_metrics` table. User/profile ownership is FK/UNIQUE, without
table inheritance. Supported SQLAlchemy Core mappings match the verified catalog;
explicit legacy compatibility mappings/read paths remain where required.

Registration saves user/profile/preferences/initial revision/event atomically.
Owner-only GET/PATCH profile APIs support validated professional information,
preferences, revision checks and immutable idempotency receipts. Clients cannot
set ownership or analytics exclusion. Existing users/projects use explicit,
locked, verified backfill from actual retained owners/registration times.

Reusable event writing replaces workflow-owned insertion without a new journal.
Versioned facts include profile, authenticated initiator, user/system executor,
source/session, occurrence/recording times, stable operation references and entity
FKs. Projectless events have the same replay/conflict rules. Old immutable events
remain intact. Payloads contain allowlisted facts/hashes/field names, not full
requests, scope documents, credentials or provider bodies.

Coverage includes profile changes; projects/draft revisions; check/estimate
admission and outcomes; regeneration/translation; saved history; feedback; CO
finalization/voiding; and existing export lifecycle events. Each logical operation
has one requested/outcome pair; physical attempts remain in the existing ledger.
Client observations establish neither authorization nor server-owned success.

## Confirmed definitions and recovery

Implemented UTC daily DISTINCT DAU, rolling 30-calendar-day MAU, stickiness,
registration/mature activation populations, TTV, exact-day D7/D30 retention,
DAU-intersected adoption, PQL, CO outcomes, per-kind/total primary operation
counts/success/median/P95/sample sizes, current feedback contributions, and
linked physical AI call/retry/token/estimated-cost/validation indicators.
All numerators and denominators consistently exclude server-flagged test/internal
profiles. Percentages use 0–100; unknown/empty/immature measurements remain NULL.

Design section11 records every explicit answer: fully elapsed seven-day activation
denominator with `[registration, registration+7days)`; terminal denominator excludes
pending/PDF; 30-minute per-user/browser sessions with shared tabs; automatic requests
do not extend inactivity; existing deletion behavior remains. PDF indicators and
session-duration KPIs are excluded. No unresolved indicator was silently enabled.

AI facts use the physical call's original UTC start date, including late results.
Retries use semantic_attempt>1 OR transport_attempt>1, once per physical call.
Incomplete totals are NULL with unknown counts; reservations are separate from
estimated cost. Existing accounting and PDF functionality remain intact. Duration
uses admitted server-operation timestamps through terminal completion, including
queue/retry time, rather than browser/network response timing.

T1 validates ownership/revision/idempotency and commits business change, revision
and confirmed event together. A forced precommit failure leaves none of them.
External model/HTTP calls hold no database transaction.

After dirty T1 commits and releases its session, T2 opens a separate UoW. A global
transaction advisory lock precedes one READ COMMITTED source projection; complete
rows and freshness metadata upsert atomically, with an additional monotonic
freshness guard. No MAX(id) checkpoint, shared concurrent AsyncSession, metrics
worker or in-memory-only recovery was introduced. T2 failure is logged and cannot
undo T1 or falsely fail its completed action.

Subsequent committed actions and `MetricsService(database.new_metrics_uow).read`
or `reconcile(start,end)` repair retained history, late facts, feedback/exclusion
changes and interrupted T1/T2 gaps. Ranges are half-open UTC dates. Idle stored
rows become stale; reading/exporting must reconcile. Direct SQL reads bypass
repair. See [service definitions](marketing-metrics.md).

## Commands and actual results

Backend commands used `../.venv/Scripts/python.exe` from `backend`, pytest cache
disabled, and owned temporary directories. All PostgreSQL/container tests owned
their disposable resources. Overlapping test runs below must not be summed.

| Check | Actual outcome |
| --- | --- |
| `python -m pytest -p no:cacheprovider --require-integration --basetemp <owned-temp>` | **730 passed in 375.21s**, including 99 integration tests; no skipped tests |
| Final affected migration/backfill/metrics/profile/workflow/worker suites | **44 passed in 84.40s**, included in full suite |
| Earlier final unit/API/architecture run | **631 passed in 77.23s**, included in full suite |
| `python -m ruff check . ../apps/api` | Passed |
| `python -m ruff format --check . ../apps/api` | **353 files** already formatted |
| `python -m mypy src/scope_guard ../apps/api/src/scope_guard_api` | Passed, 225 sources |
| Same mypy command with `--platform win32` | Passed, 225 sources; existing untyped-body notes remain |
| Frontend `npm test -- --reporter=dot` | **364 passed / 51 files in 13.72s** |
| `npm run lint` | 0 errors; existing unused `_s` warning at `lib/llm/schema.test.ts:30` |
| `npx tsc --noEmit`, `npm run build` | Passed; production build identified above |
| `python scripts/export_openapi.py --check ../ci/contracts/openapi.json` | Passed |
| Frontend `node scripts/api-types.mjs --check` | Passed; contracts regenerated only for actual profile API changes |
| `node ci/scripts/check-gateways.mjs --suite frontend` | Frontend suite passed again; backend boundaries 20 passed |
| Suites `auth-gateway`, `generation-gateway`, `drafts-gateway` | Passed; owned auth/project journeys 15 + 14, retired-generation/no-provider and saved-draft ownership checks |
| `node --test scripts/docker-entrypoint.test.mjs` | 3 passed |
| `git diff --check` | Passed |
| `python output/profile-metrics/assert_final.py` | Passed: independent DB/event/metric/delivery assertions |

The full run covers migration initialization/populated upgrade/safe reruns,
immutable history/IDs, ownership rejection, atomic rollback, T2 failure, fresh
process recovery, concurrent DISTINCT counts, post-lock freshness, atomic T2
rollback, late/midnight facts, repeated calculations, feedback replacement,
exclusions and existing worker/provider/document behavior. Formula tests cover
exact seven-day/30-day/D7/D30 boundaries and NULL behavior.

## Final-code browser evidence

Used the actual in-app browser, production frontend, real authentication, API,
existing worker/native provider bridge, controlled HTTP model responses and owned
PostgreSQL. No paid model calls. Controlled output proves collection/persistence,
not real-model quality. Installed Next.js documentation was read before edits.

Three independent synthetic profiles each registered, created a distinct project,
completed a saved check before its CO, reloaded the result, opened immutable
history, finalized a CO, regenerated a reply and translated material to Spanish.
Explicit browser login was exercised in the initial run; actual authentication
and login-only exclusions are also covered by API/integration tests. All three
complete journeys were repeated after restarting the final reviewed backend.

| Stage | Expected | Actual |
| --- | --- | --- |
| First saved analysis, before any CO | DAU/MAU 1; saved 1; CO 0; PQL 0 | Matched |
| All three journeys before extra commands | DAU/MAU 3; checks 3; CO 3; regen 3; translation 3; operations 9; PQL 0 | Matched |
| Three deliveries of one new key | One extra check, total 4; PQL 0 | Matched; three 202 responses, one run |
| Three intentional new keys with identical text | Three extra checks, total 7; qualification at third check | Matched; four distinct new run IDs across delivery experiment |
| Same key with changed content | Conflict without new check | HTTP 409; counts unchanged |
| Feedback correct then wrong | Replace contribution | correct 1→0, wrong 0→1, evaluated 1 |

Final UTC date **2026-10-17**, independently read from persisted records:

- Users/profiles/projects 3/3/3; saved checks/history 7/7; **DAU 3, MAU 3, PQL 1**; CO 3.
- **7 checks + 3 regenerations + 3 translations = 13** successful primary operations;
  failed/cancelled 0, estimate 0, success 100%, duration sample 13. Median
  **2475.251ms**, P95 **3318.19ms**.
- Analysis/CO/regeneration/translation adoption each 100% within DAU. CO finalization
  does not assert client acceptance or payment.
- **53 AI calls**,0 retries;5300 input / 1325 output tokens; stored estimated cost
  **USD 0.0079500000**;53 accepted / 0 rejected validations. Cached/reasoning totals NULL
  because the controlled provider did not report them; unknown input/output/cost 0.
- Mature activation denominator 0, activation/D7/D30 rates **NULL**; TTV sample 3,
  median **5.821s**. Fresh cohorts are not reported as 0% activation.
- **60 events**: profile.created 3, project.created 3, draft.updated 16,
  check.requested 7 / completed 7, history_saved 7, reply.requested 3 / regenerated 3,
  translation.requested 3 / completed 3, change_order.finalized 3, evaluation.changed 2.
  All are version 2 / payload 1; confirmed completion uses system executor plus the
  authenticated initiating actor. Product sessions 4 include the separate API browser.
- Definition 1; current row partial for `report_day_incomplete` and
  `ai_cached_or_reasoning_usage_incomplete`. After supported read reconciliation:
  cutoff **00:42:07.299351 UTC**, calculated **00:42:07.336992 UTC**. The requested
  empty prior day has 0 populations and NULL empty rates.

[Final DB evidence](../../output/profile-metrics/final-browser-database.json),
[assertions](../../output/profile-metrics/final-assertions.json),
[delivery stages](../../output/profile-metrics/command-deliveries.json),
[browser observations](../../output/profile-metrics/final-browser-observations.json),
[screenshot](../../output/profile-metrics/browser-final.png).
Raw logs and controlled tooling remain in ignored `output/profile-metrics/`.

## Review corrections, migration and limitations

Independent schema review passed. Final fresh-context review found and verified
corrections for: durable publications also counted by legacy revision fallback
(real regression: 3 regenerations instead of 1); manual language-change saves falsely
inferred as translation; delayed synchronous completion extending/rotating a
session (2 instead of 1); and missing browser identity before concurrent initial
hydration. Current writers preserve system executor/origin session before saving
the completion revision. Signed-cookie auth hydration uses Web Locks before the
interaction observer starts. These regressions are in the final green suite.

An earlier fixture response quoted text absent from its synthetic scope; validation
rejected it without activity/activation. Corrected input and a restarted fixture
were used for the final counts; earlier evidence is kept separately.

Only additive `0006_profile_metrics` was introduced; applied 0001–0005 are unchanged.
Backfill uses actual users/current owners, locks/verifies relationships, preserves
IDs/snapshots/receipts/accounting and immutable events, and supports safe reruns
without invented events. The nullable project-profile field is transitional;
supported writers always supply the resolved owner profile.

For a separately authorized rollout, the operator must back up/quiesce writers,
coordinate matching API/existing workers, then use the existing guarded tool:

```text
python -m scope_guard.database.cli migrate --database-url-env SCOPE_GUARD_DATABASE_URL --target 0006_profile_metrics
```

The old event conflict constraint changes: do not run old writers against 0006.
Verify exact catalog/backfill, configure existing workflow flags, start matching
API/workers, invoke reconciliation and inspect freshness/quality before use.
No real rollout was performed here.

Remaining limits: synchronous full-history T2 grows with data; idle rows require
action/read; raw SQL maintenance must reconcile; retained facts cannot reconstruct
deleted facts or past mutable feedback/exclusion values. Existing deletion behavior
is unchanged. Shared-tab initial identity requires Web Locks; simultaneous first
hydration without that API retains a compatibility limitation. The observer sends
every trusted visible interaction; high-volume coalescing is future work.
No admin UI, dashboard, export integration, metrics DB/worker, EAV or generic KPI
platform was introduced. PDF/session-duration indicators remain excluded.

Measured machine interval begins 2026-10-16 12:42:40 UTC and ends at the handoff
timestamp in ignored `WORKLOG.md`/`AGENT.md`. It includes credit pauses and idle
waiting; earlier discovery excluded. Human/billable effort is unknown.
The branch/evidence stay in place for human review; rollout/publication and later
performance/compatibility work remain operator-owned.

Final handoff: 2026-10-17 07:19:48 UTC / 2026-10-17 10:19:48 Europe/Moscow. Measured machine wall interval: 18:37:08. Includes pauses and waiting; human/billable effort remains unknown. Controlled servers stopped; the remaining stopped disposable PostgreSQL container was removed after its ownership label and all three synthetic profile IDs matched the saved evidence.
