# Product observation follow-up verification

The requested follow-up is implemented and remains uncommitted. This report
supersedes observation-delivery claims in the original implementation report;
its broader backend/browser results remain historical evidence for that version.

## Version and scope

- Branch: `codex/profile-behavior-marketing-metrics`.
- HEAD and freshly fetched `origin/main`:
  `3fe66f174807286f8d3e748b63fe89dbb91351ec`; upstream `origin/main`.
- Final application/test manifest: 603 files, SHA256
  `dd731f244e5e2d97da15c1fb15886f837bfed0a558cc9cc0dd6f4e5c31120767`.
  Manifest/evidence are in ignored `output/profile-observation-followup/`.
- Baseline browser build: `nvgzQCwgsWo1r-YwFHrge`.
  Final browser build: `sPVJje-gNesjRpD1Ps1a3`.
- The plan was saved before application code changes. Repository instructions,
  ignored `AGENT.md`, authoritative design and installed Next.js client-component
  guide were read. No backend application code, migration, authentication,
  business command, metric definition or generated contract changed in this follow-up.

## Findings and changes

The per-event HTTP traffic finding was confirmed. `product-interaction.ts` now
sends promptly on first eligible input and limits attempts to one per 30 seconds
per mounted observer, with one in-flight request. It uses monotonic browser time,
an AbortController and no timers, queues or automatic retries. Failures consume
the same interval; only a later genuine visible event can retry.

`product-session.tsx` returns the fetch promise and passes its cancellation signal.
The effect depends on user ID, so refreshed objects for the same user do not reset
the window. Cleanup disposes the observer, aborts pending delivery and removes
listeners. Old callbacks and promise settlement cannot change a new user's state.
The two adjacent test files cover traffic and React lifecycle behavior.

The transaction observation was partly a wording ambiguity: T1 already explicitly
awaited an application callback, while T2's own UoW correctly had no callback.
The backend needed no fix. `marketing-metrics.md` now describes commit, session
close/connection release, awaited application callback, independent T2 and error
logging, and distinguishes this from SQLAlchemy transaction event hooks.

Full-history synchronous reconciliation was confirmed and retained. The docs
record completion latency for business/provider-accounting commits, one global
advisory lock, growing history-dependent runtime/memory, and idle read repair.
They also describe observation timestamp approximation and delivery uncertainty.
The original verification report is explicitly labeled historical. This report,
the follow-up plan and ignored journals provide the current handoff.

## Reproduction and measured counts

| Scenario | Before | After | Evidence |
| --- | ---: | ---: | --- |
| Pointerdown +20 paired keydown/input characters +10 wheel events | 51 sends | 1 send | Controlled unit inputs, immediate assertion |
| Input each second for120 seconds, two events/second | 241 sends | 5 sends | Fake time; after at0/30/60/90/120 seconds |
| One click +20 sequential characters +10 Page Down presses | 51 HTTP requests | 1 HTTP request | Automated real browser, server request counter |

The browser used a synthetic registration/project on owned disposable PostgreSQL
at API8217/frontend3217. For each measurement, reset the test-only server counter,
click `New client request`, type `abcdefghijklmnopqrst` with sequential key
presses, then press Page Down ten times in that field. Both bursts completed in
about2.4 seconds. The after field already contained the prior autosaved text;
each measured burst added the same20 characters and ten navigation keys. This
browser check exercises keyboard scrolling/navigation attempts; wheel events
were tested as controlled unit inputs, not automated native wheel input.

The final count remained1 at the later idle evidence read. Independent database
evidence showed one shared product session for the synthetic profile and
DAU0/MAU0, successful checks0, PQL0 and AI calls0, as expected without analysis.
Test counter/evidence endpoints exist only in the ignored fixture script, not
production routes. No paid model call or manual browser check was performed.
The original three analysis/CO journeys were not repeated for this frontend-only
follow-up. Screenshot: `output/profile-observation-followup/browser-final.png`.

## Exact verification

Frontend commands, from `frontend/`:

```text
npx vitest run lib/product-interaction.test.ts
npx vitest run components/scope-guard/product-session.test.tsx
npx vitest run lib/product-interaction.test.ts components/scope-guard/product-session.test.tsx
npm test
npx vitest run tests/draft-proof-interop.test.ts
npx vitest run --maxWorkers=2
npx tsc --noEmit
npm run lint
npm run build
npm run api:types:check
```

- Utility RED:7 failed/1 passed against old code; burst actually51 vs expected1,
  continuous actually241 vs expected5. Component RED:4 failed before wiring cleanup.
- Focused final:12 passed in2.52s, including exact30-second boundary, idle time,
  slow/rejected/throwing requests, hidden/synthetic filtering, user change/logout,
  same-ID refresh, unmount/remount and React StrictMode.
- Initial full run:374 passed/1 failed due to the unrelated Python/JOSE interop
  test exceeding its existing5-second limit under concurrent checks. It passed
  alone in1.61s; no test timeout or product code was changed for it.
- Final full run with bounded concurrency:375 passed across52 files in54.32s.
- Type check passed after correcting the new test's spy type annotation.
- Lint passed with one inherited unused `_s` warning in `lib/llm/schema.test.ts`.
- Production build passed. Its configured type-check skip is covered by the
  separate successful `tsc --noEmit`. Contract freshness passed, no regeneration.
- Existing Vite configuration warning remains unchanged.

Backend command, from `backend/`:

```text
../.venv/Scripts/python.exe -m pytest tests/integration/test_profile_activity_runtime.py tests/integration/test_marketing_metrics.py tests/unit/test_database_lifecycle.py -q
```

Result:19 passed in50.15s, using owned disposable PostgreSQL only. These include
browser identity/30-minute inactivity, transactional rollback, T2 failure preserving
T1, concurrent reconciliation, late accounting, feedback and recovery tests.
No backend behavior changed; the original full730-test result was not rerun or
represented as fresh evidence. A fresh read-only reviewer found no correctness
findings in the follow-up scope and checked documentation against backend code.

## Limits and handoff

The cap is per observer, so separate tabs/remounts can each send promptly. Shared
browser identity and server inactivity rules remain unchanged. Slow requests can
suppress observations beyond30 seconds; disposal cannot undo server-accepted
requests. With prompt healthy delivery, the last submitted observation can precede
the final interaction by less than30 seconds; failures/delay can add uncertainty.
No trailing observation fills idle gaps. Full-history synchronous T2 costs and
supported read-time reconciliation requirements remain.

All earlier uncommitted implementation and unrelated files are preserved. No
commit, staging, push, PR, branch switch, worktree, reset/stash, Linear mutation
or application database migration was performed. Remaining rollout/publication
requires a separate user instruction. Human/billable effort is unknown; measured
machine elapsed time is recorded separately in ignored journals.
