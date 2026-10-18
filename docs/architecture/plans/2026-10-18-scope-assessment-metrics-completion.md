# Scope assessment and metrics completion implementation plan

Issue: user-requested integrated completion; no issue tracker changes.

## Identity, baseline and integration

- Branch: `codex/scope-assessment-and-metrics-completion`, existing checkout only.
- Fetched origin 2026-10-18; baseline `fe0e68229efbd586c5ea20cd7b488d931c699b5e`.
- Initial local main `af0ffdc34f75fdf852a69dccdbd19e158852fcc8` was clean. Its nine documentation files are preserved as untracked files on this branch; original main remains unchanged.
- `git cherry origin/main` reports all commits on profile-behavior-marketing-metrics (2714cd6,37df435), regeneration-current-commercial-terms (9c07515,9c01aa4), restore-scope-assessment-and-language (f1cd5af,16118a8) patch-equivalent to integrated commits. No branch merges or cherry-picks required. Integrated equivalents: 74a9c73,29c67f4,bbadc7d,3084c10,80c2e74,fe0e682.
- No worktrees, resets, stash, commits, pushes, remote merges, PRs or Linear edits. Preserve data. Any new application-DB migration requires user approval; disposable DB migrations authorized.

## Scope and sources

Repair existing components only. Trace parent of 336571752f3811ed8af084bfa6e9e000996bc42c through UI/types/store/schema/prompts/serialization/history. Assessment remains in interface language; replies use request candidate or explicit override; CO uses selected client-material language. Preserve explicit agreement preparation, saved commercial authority, immutable history and nonblocking diagnostics.

Metrics authority: docs/design/profile-behavior-marketing-metrics.md (resolved section 11), docs/architecture/marketing-metrics.md and original implementation plans. User is authentication identity; unique profile is activity identity. Final consumption table is marketing_metrics. No PDF KPIs, inferred traits, admin, new DB technology, external analytics or new worker.

## Definitions before repairs

- Activity: successful explicitly saved baseline check or finalized CO. Login, browsing, draft saves, translations/regeneration/estimates alone do not create DAU. Activation: first saved check in [registration,registration+7 days), denominator only fully matured registrations. TTV includes later first saved check.
- DAU unique profiles per UTC day; MAU report day plus previous 29 UTC days; DAU/MAU NULL if denominator zero. PQL >=3 saved checks and >=1 finalized CO in same 30 days. D7/D30 return on exact UTC calendar day after timely activation; incomplete current-day retention NULL. Feature adoption intersects same-day users with DAU.
- Starts on admission day; terminal outcomes/durations on terminal day. Four agreed product operation kinds: check, regeneration, translation, estimate. Success rate succeeded/(succeeded+failed+cancelled); pending/PDF excluded; empty ratios NULL. Inspect newly added agreement preparation against this existing definition before repairs.
- UTC half-open day/window boundaries. Missing observations NULL; counts zero when known absent. Medians/P95 interpolate raw samples. Current day partial.
- Product session: signed browser identity, shared tabs, 30-minute inactivity; trusted user input only. Session duration not a KPI.
- T1 persists result and source facts once. Independent T2 recomputes/upserts from post-lock consistent snapshot. Next dirty action or supported read/reconcile repairs missed updates; no new recovery worker.
- Confirmed AI calls/retries/tokens/estimated cost/validation use existing ledger, UTC physical-call start date. Unknown usage/cost => NULL with explicit unknown counters. Retries semantic_attempt>1 OR transport_attempt>1, counted once.

## Ordered steps and acceptance

- [x] Inspect instructions/Git, fetch, compare ancestry/patches, establish branch and preserve documents.
- [x] Trace complete historical assessment, restored generation/rendering/history, language overrides and saved commercial authority. Read installed Next.js guides before frontend edits. Add failing regressions for remaining defects, implement smallest repair, verify focused tests.
- [x] Trace collection API -> source facts -> separate T2 -> final table; ORM/migrations/events/idempotency/recovery/concurrency. Test discovered defects before repair; no speculative metric additions.
- [x] Run actual API/frontend/existing LLM worker with controlled provider and disposable PostgreSQL only. Register/login/create/check/reply/language/explicit agreement/edit/regenerate/history; repeat identities. Capture provider language/commercial payloads and browser evidence.
- [x] Exercise key replay/double click/two tabs/failure/repeated reconciliation/T2 fault recovery. Use controlled timestamps separately for period boundaries; independently reconcile every final column using reference SQL, not production aggregation.
- [x] Run focused and necessary full checks; record every initial failure. Rebuild affected local images, check active operations before matching backend/worker replacement. Preserve application DB and do not migrate it without required approval.
- [x] Save architecture report with scenario/column reconciliation tables, historical references, test/browser evidence, controlled-vs-live distinction, remaining defects and actual running versions. Update ignored AGENT.md/WORKLOG.md locally only.

## Evidence and handoff

Owned evidence directory: output/scope-assessment-metrics-completion/ (ignored). Report: docs/architecture/2026-10-18-scope-assessment-metrics-completion.md. Owner: current chat. Controlled-provider evidence proves integration, not live model quality; no paid calls authorized. Any blocked acceptance remains explicitly BLOCKED.

Verification qualification: broad backend/integration acceptance remains BLOCKED; initial same-key500 remains FAIL. See final report. Completed checklist means work performed and limitations recorded, not unconditional acceptance.
