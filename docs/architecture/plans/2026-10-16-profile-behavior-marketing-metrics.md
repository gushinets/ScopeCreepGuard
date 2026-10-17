# Profile, behavior and marketing metrics Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for task execution and review. Steps use checkboxes. User instructions override skill defaults: current checkout, no worktree, no commits or publication, no brainstorming, and no assumed answers to open decisions.

**Goal:** Persist professional profiles and reliable behavior facts, and calculate one wide daily marketing table without compromising business transactions.

**Architecture:** Reuse PostgreSQL, SQLAlchemy repositories and UoWs. A confirmed action saves its change/revision/event together (T1); an independent service reconciles committed source facts into marketing_metrics (T2). Serialize reconciliation before reading, use one consistent source snapshot, recompute facts instead of incrementing counters, and recover through subsequent actions and explicit reads.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 17, Alembic, Next.js 16.3, pytest and existing controlled browser/provider tooling.

**Spec:** docs/design/profile-behavior-marketing-metrics.md (untracked authoritative input; preserve it).

## Identity, base and constraints

- Discovery ticket ANY-689 is data clarification only; no status/scope mutation.
- PR 24 merged at 2026-10-16 11:03:37 UTC. Fetched approved base: origin/main, 3fe66f174807286f8d3e748b63fe89dbb91351ec.
- Branch: codex/profile-behavior-marketing-metrics, new branch in current checkout. Previous branch and history remain intact. Previous local 8450bbe model-default commit is outside the requested approved base and remains on its original branch.
- Preserve unrelated .gitignore diff, all three untracked design documents, ignored configuration, AGENT.md, WORKLOG.md and local evidence. Never migrate an application DB.
- One user/one profile by FK and UNIQUE, no table inheritance. Reuse all current product tables and IDs, immutable snapshots, provider ledger and idempotency receipts.
- No dashboard/admin/export integration, metrics database/worker, EAV platform, AI profiling, external enrichment, CRM, billing or authentication redesign.
- UTC report dates and half-open calendar windows; 30-day MAU includes report date. Percentages are 0–100. Unknown/empty/immature values are NULL. Every population excludes test/internal profiles.
- Meaningful activity is successful saved baseline analysis OR confirmed CO finalization. Regeneration/translation/estimate/PDF/login alone do not establish activity.
- Model/HTTP calls never hold database transactions. Never share AsyncSession between concurrent tasks.

## Explicit decisions

Bundled questions were sent before implementation, and the user explicitly resolved them during schema work:

1. Include AI calls/retries/tokens/estimated cost/validation indicators linked to user operations, using existing provider accounting. Exclude PDF-export indicators. Existing ledger/PDF functionality remains intact.
2. Activation denominator is profiles with a fully elapsed seven-day registration window; numerator is activated profiles within the same mature population. Activation interval is `[registered_at, registered_at + 7 days)`. Terminal operation success is succeeded / (succeeded + failed + cancelled), excluding pending/PDF, expressed 0–100; empty denominator NULL.
3. Thirty-minute session inactivity; same user/browser shares across tabs, different browsers/devices separate. Polling and automatic requests do not extend activity. Session expiry is distinct from auth expiry and DAU/MAU. Session Duration is outside this KPI scope.
4. Preserve existing deletion behavior, add no deletion/anonymization policy, and document analytics limitations.
5. AI indicators use physical-call UTC start date, including eventual usage/cost/validation; late updates rewrite that original date. Retry is semantic_attempt > 1 OR transport_attempt > 1, counted once per physical attempt. Ordinary stages/first reviewer calls are not retries. Incomplete token/cost totals are NULL with unknown-call counts; unresolved reservations are excluded from estimated cost. Explicitly confirmed in a follow-up question.

The original open questions remain in the design as history; section 11 records the explicit resolutions. All corresponding confirmed calculations now belong in Tasks 1–3.

## Repository observations

Alembic head is 0005_llm_workflow. Baseline ORM classes still describe retired Drizzle-era draft/history fields; active workflow repositories use specialized SQL, while some compatibility read paths still use those ORM classes. WorkflowSQLRepository.event currently silently ignores changed duplicate content and cannot safely deduplicate projectless events. Auth registration currently inserts only users. Immutable event triggers prohibit runtime backfill updates. Revision-specific catalog verification must accommodate the additive revision rather than accepting arbitrary drift.

## Task 1: Additive schema, ownership backfill and supported mappings

**Files:** create backend/alembic/versions/0006_profile_metrics.py, backend/src/scope_guard/database/models/profiles.py, backend/src/scope_guard/database/models/activity.py, backend/src/scope_guard/database/models/marketing.py and backend/src/scope_guard/database/profile_backfill.py; modify models and schema_verification.py only as required; add backend/tests/integration/test_profile_metrics_migration.py and unit mapping tests.

**Interfaces:** profiles are resolved by user_id; projects carry profile_id with a composite FK proving profile/user ownership. New event fields support projectless events and stable (source, deduplication_key) identity. marketing_metrics has explicit nullable typed KPI columns from spec section 5. profile backfill is explicit, verified and rerunnable.

- [x] Write migration tests that initialize empty schema, upgrade a populated 0005 schema and rerun verified backfill without changing old IDs/history/event contents.
- [x] Add profiles (id/user_id/names/profession/status/revision/timestamps and explicit analytics exclusion), profile_preferences, immutable profile_revisions, product_sessions and wide marketing_metrics. Validate revision/allowed preference values/timestamp ordering.
- [x] Backfill one profile per existing user from actual registration time. Add project ownership safely and enforce consistent user/profile/project/session/actor links. New project writers must resolve owner profiles on the server.
- [x] Extend activity_events additively. Preserve old rows byte-for-byte, using nullable legacy extension fields or a verified migration-only backfill procedure; preserve immutable protection. Add typed new-version contracts and projectless idempotency.
- [x] Correct active supported mappings; retain explicitly named compatibility mappings for old-schema paths only where still needed. Do not modify applied migrations or weaken existing catalog validation.
- [x] Run disposable PostgreSQL migration tests and schema/mapping unit tests. Record failures as failures, including unavailable Docker. Leave changes uncommitted.

Representative invariant:

```python
assert old_history_after == old_history_before
assert old_events_after == old_events_before
assert profile_count == user_count
assert inconsistent_project_owner_rejected
```

## Task 2: Profiles, atomic registration and reusable confirmed events

**Files:** create domain/profiles, domain/activity and services/profiles/service.py, services/activity modules and database/repositories/profiles.py, database/repositories/activity.py under backend/src/scope_guard; modify repositories/users.py, repositories/workflow.py, services/auth/use_cases.py, existing workflow/LLM/evaluation writers and apps/api composition/routes/schemas. Add focused unit/API/integration tests. Frontend forwarding changes, if needed, require installed Next documentation first.

**Interfaces:** EventRepository.append accepts a typed immutable event, returns existing identical receipt, and raises conflict on changed content. ProfileService reads/updates authenticated owner's profile/preferences using expectedRevision and operationId; update stores profile revision and event in T1. Registration creates user/profile/initial revision/profile.created atomically.

- [x] Write failing tests for atomic registration, precommit rollback, cross-owner profile access, CAS updates and same-key replay/content conflict.
- [x] Extract event insert logic from WorkflowSQLRepository into a reusable repository; keep its old method as an explicit delegating adapter while callers migrate. Validate existing entity links, actor/initiator/executor, source/version/timestamps and safe allowlisted payloads; never copy full user content.
- [x] Implement professional profile/preferences read and revisioned update through existing authentication; no profile_id is trusted from clients. Do not expose analytics exclusion flags for self-service changes.
- [x] Integrate confirmed project/draft/check/regeneration/translation/estimate/evaluation/CO events into existing UoWs. Treat each logical operation once; provider attempts stay in existing ledger. Preserve late applied=false successful saved checks.
- [x] Add product-session assignment with the confirmed 30-minute per-user/browser rule, sharing across tabs. Only explicit user interaction extends it; background polling and automatic requests do not. Session metadata never authorizes success.
- [x] Run focused units and authenticated API tests with independent DB verification; test three deliveries of one command and three intentional different keys. Leave changes uncommitted.

```python
first = await events.append(event)
assert await events.append(event) == first
with pytest.raises(EventConflict):
    await events.append(changed_event_same_identity)
```

## Task 3: Wide metrics service, isolated T2 and recovery

**Files:** create backend/src/scope_guard/domain/marketing, services/marketing/service.py and ports.py, database/repositories/marketing.py; wire after-commit reconciliation through composition/UoW boundaries without database imports in services. Add unit formula tests and PostgreSQL/API metrics tests.

**Interfaces:** MetricsService.reconcile(start: date, end: date) and read(start, end) operate through a new metrics UoW; read reconciles relevant windows. A safe after-commit adapter logs T2 failures while preserving T1 result. Do not use MAX(id) as a checkpoint.

- [x] Write deterministic UTC source-observation tests for distinct DAU/30-calendar-day MAU, adoption restricted to DAU, three-check-plus-CO PQL, first saved value/TTV and changed feedback replacing prior contribution.
- [x] Calculate all confirmed wide columns using original source observations, retaining source sample sizes and NULL unknowns. Include mature-cohort activation, half-open seven-day boundary, D7/D30 retention and terminal operation success rates. Starts use admission date; outcomes/durations use terminal date, including queue/retries. Include linked AI accounting indicators from the provider ledger; exclude PDF metrics.
- [x] Serialize before snapshot acquisition using transaction locks in stable order, then read a consistent committed source snapshot. Full affected-window reconciliation is acceptable and safer than a speculative checkpoint. Atomically upsert metrics plus freshness/definition version/typed partial-data notes; older calculations cannot overwrite newer results.
- [x] Invoke T2 only after committed actions with separate UoW/session. T2 errors cannot fail the completed user API action. Explicit read/reconciliation repairs idle expiry, late facts, feedback edits and interruption between T1/T2. No in-memory background task as sole recovery.
- [x] Prove rollback, T2 failure, restart gap, concurrency, late/midnight events, repeat reconciliation and internal/test exclusions with disposable PostgreSQL. Leave changes uncommitted.

```python
assert metrics.dau == 1
assert metrics.mau == 1
assert metrics.analysis_adoption_percent == 100
assert empty_window.stickiness_percent is None
```

## Task 4: Final verification, browser repetitions and handoff

**Files:** add test tooling only under existing test/evidence conventions; update this plan, docs/architecture/2026-10-16-profile-metrics-verification.md, ignored AGENT.md and WORKLOG.md. Do not edit unrelated design documents.

- [x] Run backend units/API/architecture, required disposable PostgreSQL suites, affected frontend tests, Ruff/format, both mypy platforms, frontend lint/types and contract freshness. Regenerate contracts only for actual profile API changes.
- [x] Exercise actual browser with controlled providers on three independent synthetic profiles: register/login, create/open project, saved analysis without CO, reload, applicable CO finalization, regeneration/translation exclusions and independently read events/metrics. Record expected/actual observations and exact tested version.
- [x] Separately exercise triple delivery of one operation key and three distinct-key intentional checks. Do not claim controlled fixtures prove real-model quality.
- [x] Review final diff for ownership leaks, event loss/duplication, erroneous windows/denominators, T2 contamination of T1, NULL masking and scope expansion. Fix reproducible in-scope defects and rerun affected checks.
- [x] Document additive migration/backfill/rollout procedure without applying to real data. Record unresolved/disabled indicators, idle freshness limits and all blocked/incomplete verification honestly.
- [x] Final report includes branch/base, reused/new tables, event coverage, metrics/gates, T1/T2/recovery, actual commands/outcomes/browser counts, remaining limitations and rollout steps. No commit/push/PR/merge/Linear status change.

## Progress and evidence

- 2026-10-16: instructions/spec/ignored handoff read; origin fetched; PR merge confirmed; approved branch created with original local files preserved. Decision questions pending. No application code edited before plan.
- Measured execution interval starts 2026-10-16 12:42:40 UTC; earlier discovery time not included. Human/billable effort is unknown.
- Task 1 complete and independently reviewed: specification PASS, quality PASS. Focused owned PostgreSQL/current+baseline suite: 36 passed in 31.54s; focused unit boundaries: 26 passed in 1.45s (overlap). The migration is not independently deployable until Task 2 replaces the event writer and supplies project ownership.
- Initial Task 2 dispatch stopped before edits because of an account usage limit. User requested continuation; the same implementer resumed. Elapsed machine time includes that interruption.
- Tasks 2 and 3 complete. Final review corrections verified: durable publication revisions no longer double-count; manual language-change saves do not establish translation; synchronous completion retains system executor/origin session; auth hydration installs the browser identity before the observer starts. Task 4 final browser repetitions are in progress on a restarted final-code fixture.


- 2026-10-17 07:19:48 UTC: Task 4 complete. Final full backend 730 passed/375.21s; frontend 364 passed/13.72s; all static/contract/build checks passed with one inherited frontend lint warning. Three final-code browser journeys and final delivery/feedback experiment independently asserted DAU3/MAU3/checks7/CO3/operations13/PQL1/AI53/events60. Read reconciliation verified. Final report: ../2026-10-16-profile-metrics-verification.md. Web Locks fallback, full-history cost, idle freshness and deletion-history limits are explicit. Branch remains uncommitted and unpublished; rollout belongs to the operator.
