# ANY-549 — autosave and conflict recovery

Base: fetched origin/main d1239e7. Branch: codex/any-549-autosave-conflict-recovery.
Approved workflow: clean shared checkout; other chats idle; no worktrees, stashes,
resets, commits or publication. AGENT.md and WORKLOG.md remain ignored.

Scope: explicit user field patches applied to the current Draft under existing
transaction locks and revision CAS, command receipt deduplication, bounded transport
retries, durable local recovery and localized save feedback. Same-field winner is
server application order. No offline typing chronology or text merging is inferred.
Legacy full-document writes and all non-edit commands retain strict revision checks.
AI publication, historical snapshots, ownership, History/Draft boundaries stay intact.
Excluded: translation semantics/currency, AI validation, PDF and marketing definitions.

Steps: inspect existing paths and Next client documentation; implement edit patch
contract and queue; regenerate contracts; add focused regressions; execute disposable
PostgreSQL/frontend checks and synthetic browser scenarios; record evidence below.

Implementation: PUT /api/v2/drafts/{id} accepts either the existing strict `changes`
payload or an explicit flat `patch`. Allowed paths are requestText, reply.text,
reply.tone and user-editable Change Order fields. additionalCost/currency/
noAdditionalCharge travel together. Omitted values stay untouched; empty strings
clear fields. Language, generated variants, analysis, provenance and identity cannot
be patched. The existing lock orders commands; repository revision CAS remains.
Receipt identity/hash is checked again after locking. Replays return current
canonical state without another revision. The SQL repository/schema is unchanged.

Client: one in-flight command, existing 750 ms debounce / 5 s maximum, immutable
uncertain commands, separate coalesced pending field intent, canonical acknowledgement
overlaid with only newer intent. Three transport attempts with 500/1500 ms delays;
each autosave request times out after 15 seconds. Network errors, 408, 429 and 5xx
retry; other 4xx stop immediately. A definitive rejection queues the latest intent
under a new identity on manual Retry. Unknown outcomes reuse the original identity
before sending newer changes. Further typing after exhaustion does not restart an
automatic loop. Recovery retains pending patches/uncertain identity across reload,
scoped by owner/Draft/tab; acknowledgement alone clears the active buffer.
Save/recovery feedback is now rendered in the shared workspace, in English/Russian.

Verification (2026-10-19):
- Frontend focused autosave/controller/store/transport suite: final 49 passed,
  including repeated reload of an uncertain command against a newer revision and
  non-JSON gateway error responses.
- PostgreSQL workflow suites: 22 passed (persistent_workflow, nonblocking_workflow,
  llm_workflow). Includes distinct/same-field stale patches, concurrent duplicate
  delivery, replay after a newer save, immutable revisions/history, ownership,
  strict stale restore and existing late-result safeguards. Updated late-AI test
  also passed with the new patch path (1 passed, 9 deselected).
- API/domain tests: 12 passed, including clear/omission, mixed payload rejection,
  protected fields and coupled commercial values.
- Final TypeScript, changed-file ESLint, Ruff (7 files), OpenAPI/type freshness and
  diff checks passed. API/domain rerun: 12 passed, with a harmless sandbox pytest
  cache write warning. Installed Vite also reports its existing config-loader notice.
- Real headed Chromium, two actual tabs, actual Next editor/gateway and editing
  service on fixture-owned disposable PostgreSQL: different fields both survive;
  later same-field command wins; stale saves return 200; canonical untouched fields
  refresh; forced 503 makes three identical attempts, leaves server unchanged and
  displays failure/Retry; continued typing triggers no further loop; confirmed
  reload offers recovery; recovery reuses uncertain ID then saves newer typing;
  manual Retry preserves newest text; explicit empty reply clears successfully.
  Screenshots and synthetic HTTP evidence are local/ignored under
  output/playwright/any-549/. The failure screenshot was visually inspected.

Harness corrections: initial frontend run hit sandbox Vite rename restrictions;
rerun outside that sandbox succeeded. AI integration initially ran from the wrong
directory; backend-directory rerun passed. Browser fixture needed Windows selector
loop and explicit allowed test origin. C: then ran out of disk space; the cached
CLI completed scenarios without downloads. No unrelated files were deleted.
The later final-check attempt was blocked by automatic approval review's account
usage limit; after the user requested continuation, all final checks above ran.

Final cleanup: task browser and frontend/API processes stopped; browser artifacts
moved into ignored output. next-env.d.ts restored to its pre-dev contents.
Docker is unavailable on continuation, so cleanup of this task's remaining
disposable fixture container could not be verified/completed:
1e61d9842c9f (scg-any639-test-8bc0a59f9e03497799cf6fff12d5b2d6).
Do not remove the older unrelated disposable container found alongside it.

Limits: no chronological ordering of offline typing across devices and no text
merge. Untouched tabs refresh on acknowledgement/reload, not through live push.
Legacy full-snapshot callers retain strict conflict behavior; old recovery buffers
without field intent retain their existing conservative revision check. Recovery
durability depends on browser storage availability. No production build or broad
unrelated suite was required; only focused checks ran. No paid provider calls,
application-database migration/mutation, commits, pushes, PRs or Linear writes.
Follow-up owner: reviewer of this uncommitted branch.
