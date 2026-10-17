# Profile observation and transaction documentation follow-up

> **For agentic workers:** Use superpowers:executing-plans inline. User instructions override skill defaults: implement after this plan, no brainstorming, worktree, commit or publication. Preserve the existing uncommitted implementation.

**Goal:** Bound session-observation traffic and accurately document the existing synchronous reconciliation path.

**Architecture:** Keep a small observer-local leading-edge limiter: the first eligible interaction sends immediately; subsequent genuine visible interactions may send only after 30 seconds and after the previous request settles. No timers or queued/trailing observations. Cleanup aborts an outstanding request and permanently disposes that observer. Metrics/backend behavior remains unchanged.

**Tech stack:** Existing React/Next.js16.3, TypeScript, AbortController, monotonic browser time, Vitest fake time and controlled requests; existing owned PostgreSQL session tests.

**Spec:** User attachment `a8be9d3d-9dbc-446c-9019-94fed5c20c8b/Вставленный текст.txt`; existing `docs/design/profile-behavior-marketing-metrics.md`, supplemented by this explicit coalescing request. ANY-689 remains background clarification only.

## Base, checkout and constraints

- Branch `codex/profile-behavior-marketing-metrics`; HEAD and fetched `origin/main` are `3fe66f174807286f8d3e748b63fe89dbb91351ec`; upstream `origin/main`. Fetch completed without changing checkout files.
- Preserve all existing tracked/untracked implementation, unrelated `.gitignore`, both unrelated workflow designs, authoritative design and ignored configuration. No switching/reset/stash/worktree, publication, Linear change or real DB migration.
- Read repository/ignored instructions and installed Next.js `05-server-and-client-components.md` before frontend changes.
- No changes to business commands, confirmed events, auth/browser identity, 30-minute session timeout, DAU/MAU, accounting, migrations or T2 algorithm.
- Maintain at most one send per 30 seconds per mounted observer and at most one in-flight send. Failure consumes that attempt's window; only another eligible real interaction may retry.

## Review focus

- Paired keydown/input plus wheel bursts: one immediate request, no trailing send.
- Continuous activity: new requests at eligible 30-second boundaries, independent of event cadence.
- Slow/rejected/throwing requests: no overlap, unhandled rejection or automatic retry.
- Hidden/synthetic input and idle time: no requests, timers or success claims.
- Logout/user changes/remount/StrictMode: old requests abort; disposed callbacks cannot send or alter the next observer; same-user object refresh does not reset the window.

## Task 1: Bound observations and prove lifecycle behavior

**Files:** modify `frontend/lib/product-interaction.ts`, its test, and `frontend/components/scope-guard/product-session.tsx`; create `product-session.test.tsx` alongside the component.

**Interface:** Keep callable `interactionObserver(send, now?)`; `send(signal)` may return a promise; add `dispose()`. Use monotonic time by default, an AbortController per send and observer-local last-attempt/in-flight/disposed state. The component keys its effect by authenticated user ID and disposes/removes listeners on cleanup.

- [x] Record a reproducible before count: pointerdown1 +20 paired keydown/input characters +wheel10 =51 eligible events. Add a failing assertion expecting one immediate send and run it against current code.
- [x] Add fake-time cases for 30-second boundaries/continuous input, idle after a burst, slow requests, rejection/synchronous throw, ignored input, disposal and fresh observers.
- [x] Implement the minimal leading-edge mechanism with no timer, queue, retry task or dependency; wire fetch cancellation and stable user-ID lifecycle.
- [x] Add component tests for listener cleanup, logout, user replacement, same-ID refresh, remount and React StrictMode.
- [x] Run focused/full frontend tests, type/lint checks and existing browser-identity tests. Reuse owned disposable PostgreSQL session tests to confirm the server's inactivity semantics remain unchanged.
- [x] If feasible, use a controlled local browser fixture to measure typing/scroll requests before/after. Label pure unit/jsdom, automated real-browser and manual evidence separately; do not claim a manual check if none ran.

## Task 2: Precise documentation and reviewable handoff

**Files:** update `docs/architecture/marketing-metrics.md`, annotate the original verification report as historical, add `docs/architecture/2026-10-17-profile-observation-verification.md`, update this plan and ignored `AGENT.md`/`WORKLOG.md`.

- [x] Document T1 commit → release/close session → await explicit application callback → independent T2 UoW/session. Distinguish this from SQLAlchemy transaction event hooks; T2 has no callback to prevent recursion. Preserve logging/failure isolation.
- [x] Document synchronously awaited full-history reload/recalculation, completion latency, global serialization, history-dependent runtime/memory and idle read-time freshness. Keep algorithm/checkpoints/cache/background behavior unchanged.
- [x] Document leading-edge timestamp approximation: the last successful observation can precede the final interaction by under30 seconds with healthy prompt delivery; network/in-flight/failure gaps can add uncertainty. No client timestamp becomes authoritative; inactivity remains30 minutes from retained server observations/business activity.
- [x] Review the follow-up diff, record exact commands/counts and remaining limitations, verify unrelated files preserved, update journal with measured wall time versus unknown human/billable effort, and leave everything uncommitted.

## Progress

- Plan prepared before application code. Findings confirmed: every eligible event currently sends; reconciliation reloads all retained facts/days; T1 explicitly awaits an application callback while T2 itself has none. Execution starts after this plan without an approval pause, as explicitly requested.


## Verification and handoff

- Utility RED7/8 and component RED4/4 observed before their respective fixes; focused final12/12 passed. Full frontend375/52files passed with maxWorkers2 (54.32s), types/lint/build/contracts passed; inherited lint/Vite warnings retained.
- Existing backend session/metrics/lifecycle19/19 passed (50.15s) on owned disposable PostgreSQL. Backend implementation unchanged.
- Automated real-browser burst: one click +20 sequential characters +10 PageDown presses, baseline51 requests, final1. Native wheel tested in unit inputs only. No manual browser check. Evidence/report: ../2026-10-17-profile-observation-verification.md.
- Ruling: use bounded concurrency for final frontend suite after an unrelated5s proof-interop timeout under concurrent checks; isolated interop passed without a code/timeout change. Cost: longer suite elapsed time.
- Independent focused final review: no correctness findings; no declined judgments or deferred minors. Prior large implementation review remains historical; this follow-up reviewed only its own changes.
- Follow-up ownership: a human may review/publish separately; later scaling work must preserve recovery/snapshot semantics. Leave implementation uncommitted.
- Preservation:674 prior nonignored files checked; no missing/unexpected changes. Temporary fixture and browser closed; disposable-container label inventory empty. Ignored journals record measured wall1:06:58, human/billable effort unknown.
