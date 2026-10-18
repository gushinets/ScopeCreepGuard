# Bounded current-main acceptance campaign

Goal: execute one acceptance campaign with exactly 20 planned live user-operation slots; distinguish operation completion, content quality and coverage gaps.

Base/branch: existing checkout, local `main`, fast-forwarded from `29c67f4` to fetched `origin/main` `d3544de711171619d901241ca0e763da0702f4cb`. No worktree, stash, reset, divergent merge or product edits. The previous branch has four SHA-distinct commits but its complete tree equals current main. Six untracked documents and ignored local files are preserved.

Execution: primary agent inline, as explicitly requested (plan then execute). No implementation, commits, publication or Linear writes. Evidence in `output/e2e/20261018-main-20-d3544de/`; final concise report in `docs/architecture/2026-10-18-main-20-operations-acceptance.md`.

Requirements: user campaign specification; current `docs/design/project-draft-ai-workflow.md`, `2026-10-17-nonblocking-full-acceptance.md`, `2026-10-17-commercial-presentation-execution-lanes.md`; five Linear descriptions and latest Mikhail Gushinets comments (15 October, pagination exhausted). Retained original fixtures are inputs/evidence only, never previous-run passes or authorization.

## Limits and policy

- Twenty user submissions maximum, failures consume slots. Block dependent cases; no substitute paid results.
- Fresh user authorization received 18 October: 80 aggregate external calls, USD1 conservative accounting ceiling, 90 minutes after first paid dispatch, earliest limit wins. Every diagnostic/retry shares a new persistent SQLite guard. No historical ledger.
- Intended requested and returned model `gpt-6-luna`; mismatch stops further calls. Reservation rates USD0.0000003/input token and USD0.000001/output token are conservative accounting bounds, not an invoice.
- Estimated ordinary total: 32 generation stages plus roughly 22–28 diagnostic calls; remainder reserved for internal structural/transport retries. Unknown outcomes retain full reservation.
- Main/replies publish independently; agreement only on explicit request; content/reviewer findings are internal nonblocking diagnostics. JSON, ownership, revisions, persistence, idempotency and budgets still enforce failures.
- Older Linear invalid-content rejection criteria remain explicitly unsatisfied by diagnostic-only publication. Never weaken expectations or repair product during acceptance.

## Fixed operation slots and pre-dispatch oracles

The Price Monitor contract excludes Arrow/email and includes one unused revision for threshold/format changes. MXN conversion is unspecified. Yoga includes colour/reordering changes, excludes additional standalone pages and advertising creatives, and leaves new sections unestimated. Original retained contracts and exact requests are recorded in fixtures before dispatch.

| Slot | Kind | Fixture / expected |
|---:|---|---|
|1|check|RU UI / RU threshold and formatting / included|
|2|check|RU UI / original EN Yoga darker buttons/reorder / included|
|3|check|RU UI / ES Yoga additional standalone booking page / excluded|
|4|check|EN UI / RU Arrow/email with legitimate URL/email/technical names / excluded|
|5|check|EN UI / exact original EN Arrow/email / excluded|
|6|check|EN UI / ES MXN without conversion details / ambiguous|
|7|check|Exact slot 3 scope/request/UI repeated with new key; selected before any results|
|8|check|After manual override on slot 5, fresh RU complaint / automatic RU; included threshold change|
|9|agreement|Successful slot 4 Russian result, explicit preparation (selected before agreement dispatch to cover a different preparation language from slot 10)|
|10|agreement|Successful slot 5 translated Spanish result, explicit preparation|
|11|regenerate|Warm on slot 5; only selected tone changes|
|12|regenerate|Neutral on slot 5; only selected tone changes|
|13|regenerate|Firm on slot 5; only selected tone changes|
|14|regenerate|Historical slot 5 after current scope includes Arrow/email; preserve original exclusion and current manual 2.5h/175.35USD|
|15|translate|Slot 5 replies-only EN to ES before slot 10; no agreement created|
|16|translate|Edited slot 10 agreement ES to EN; manual prose/terms preserved|
|17|translate|Same agreement EN to ES; working-day/approval meaning preserved|
|18|estimate|Slot 10 manual 2.5h/175.35USD/3 working days after approval; project 80EUR/hour|
|19|estimate|Same unchanged commercial inputs, new operation key|
|20|estimate|Same unchanged commercial inputs, new operation key|

Execution dependencies: 1–7; 15; 9/10; edited agreement 16/17; clean restoration; 18–20; 11–14; 8. Slot 8 runs last so its new result cannot displace the saved predecessor needed by historical regeneration. Reorder only to satisfy dependencies without changing slots. Close a tab during one planned regeneration; recover with clean login. Cancel manual replacement before dispatch, then perform its one planned submission.

## Ordered work

- [x] Read repository instructions, inspect initial Git state, fetch, switch existing main, fast-forward only, verify HEAD/upstream and clean tracked tree.
- [x] Read current requirements and five Linear issues/comments; verify required implementation exists in main.
- [x] Save source/preserved-file hashes, fixture oracles, fresh authorization and empty 20-slot ledger.
- [x] Use source-verified current-main production frontend copy (fresh build blocked by font network; retained production artifact documented), discover/apply migration head to owned disposable PostgreSQL only. Run actual API and existing LLM/export entrypoints with matching flags, Origins, auth and private export storage. Record versions/configuration without secrets.
- [x] Use in-app browser first (availability probe succeeded); no external browser without permission. Register synthetic accounts; inspect real controls.
- [x] Execute fixed live slots once. Read all generated prose and record automatic History, language/scope/commitments, agreement independence, removed UI absence. Capture first material failure immediately; continue independent slots.
- [x] Using same results, edit 200EUR/dedicated rationale, paid/free/paid via UI; inspect preview, actual clipboard, archive/finalize and browser worker-PDF download; render every page; reload and restore paid values without generation.
- [x] Verify clean login without storage cloning, History read-only, immutable archives/artifact bytes, replay no generation, changed-key payload conflict, anonymous/foreign isolation across projects/drafts/operations/history/exports.
- [x] Run only four controlled cases with disposable resources: held diagnostic/user completion through production scheduler; shared TS/Python free projection parity; malformed reviewer preserves completed main; malformed generator JSON genuinely fails and preserves content. No previous adversarial matrix/full suite.
- [x] Drain/account diagnostics, verify guard bounds, compare final source/preserved hashes, stop/remove only owned resources. Save concise report and sanitized evidence index.

## Evidence and handoff

Track submission/admission keys and status, before/after persisted snapshots, all three replies, diagnostics separately, requested/returned models, physical calls/retries/cost reservations/usage/latency. Never include credentials, cookies, auth proofs or signed URLs. New helper code stays inside ignored evidence; no product/test expectation changes.

Final report includes 20 rows (PASS/FAIL/BLOCKED/NOT RUN), version/build/config, each operation family, clipboard/PDF/reload evidence, scheduling result, Mikhail mapping/old-vs-new policy, coverage limits and cleanup. End with four requested acceptance answers. Human acceptance belongs to the project owner; this bounded sample is not exhaustive certification. WORKLOG records actions without invented hours; AGENT.md and WORKLOG.md remain ignored.


Completed: 20/20 operations, 52 provider calls, USD0.0500898 conservative accounting. Four regeneration content failures; no fixes or added live cases. Two separately authorized external non-AI checks passed against the restored actual database with paid dispatch closed. Owned resources removed; report and evidence index contain limitations.
