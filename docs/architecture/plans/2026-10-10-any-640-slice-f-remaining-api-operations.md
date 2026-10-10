# ANY-640 Slice F — remaining FastAPI operations

Approved in chat on 2026-10-10. Execute inline with test-driven development;
retain this plan as the execution ledger and do not commit or push.

**Goal:** Transfer manual history creation, evaluation labeling/export and locale
writes to FastAPI while preserving the existing HTTP and persistence contracts.
**Starting HEAD:** `e9fd72300ef75aa05deccbad2ad09522de62185f` (committed Slice E).
**Branch:** `codex/any-640-fastapi-business-workflows`.
**Base:** ANY-639 `97518baacaba56a1a2542fe145b14d62644c5fda`.
**Checkout:** Current checkout; preserve `dev.sh`, `docker-compose.override.yml`,
`pnpm-workspace.yaml`, `test_openai.mjs`, and ignored `AGENT.md`. No branch/worktree,
staging, commit, push, PR, migration, deployment or application-database changes.

## Architecture and interfaces

FastAPI routes own raw object parsing, validation precedence, cookies, headers and
error mapping. Project and evaluation use cases own workflows and transaction
orchestration. Repository ports exchange frozen detached values; SQLAlchemy adapters
own owner-filtered reads, inserts, updates, upserts and row serialization. The
existing UoW owns commit, rollback and close. Drizzle remains migration authority.

Manual history checks authentication and owner-scoped project existence before body
parsing. It accepts a shaped `YYYY-MM-DD`, trims request/summary, inserts one entry,
updates `lastChecked`, and commits once. It never creates drafts/evaluations, changes
snapshots, or calls generation.

Evaluation parsing preserves UUID/reasoning/accuracy/human-verdict order. Owned
history supplies the stored request/AI verdict and current project scope/industry.
Upsert retains one row per history entry. Export filters by evaluation owner, orders
by `createdAt,id`, and emits exact compact UTF-8 JSONL with a final newline only for
nonempty output. Locale stays public and writes the existing one-year cookie.

All four Next handlers become one-call forwarders. Origin protection remains in
Next; Python authenticates the three protected operations. There is no retry,
fallback or dual write. Prompts, generation, drafts, snapshots, pricing, PDFs,
project CRUD and browser behavior remain unchanged.

## Ordered execution

- [x] Freeze validation, persistence, JSONL, cookie and gateway regressions; observe
  the missing Python routes/behavior fail.
- [x] Implement manual history values, port, use case, adapter and route atomically.
- [x] Implement evaluation values, port, use cases, adapter, routes and exact export.
- [x] Implement locale route/cookie, cut all four Next routes to forwarding, and
  retire operation-specific production TypeScript business modules.
- [x] Regenerate OpenAPI/types; update ownership, verification and ignored handoff;
  run full verification and independent review.

## Compatibility and tests

History errors: malformed body, invalid date shape, blank request, invalid verdict
and blank summary retain their existing 400 codes; missing/foreign project is 404;
unexpected persistence failure is generic 500. Database-invalid calendar dates remain
persistence errors. Tests prove rollback after insert/update/commit/cancellation and
zero draft/provider side effects.

Evaluation tests cover correct/wrong/debatable rules, prohibited present-null
`humanVerdict`, trimming and validation order, malformed/missing/foreign history,
replacement/concurrency, preserved creation identity/context, and two-user isolation.
Export tests assert exact field order/casing/UTF-8 bytes/timestamp-ID ordering/headers,
empty bytes and final newline, including unlinked owned evaluations.

Locale tests assert invalid-body/locale errors and development/production cookie
attributes. Gateway tests assert raw forwarding, headers/cookies/cancellation, one
attempt and backend-outage mapping. OpenAPI contains all 21 operations and generated
frontend types are fresh.

Run backend unit/API, disposable PostgreSQL integration and full suites; Ruff lint
and format; mypy; OpenAPI check; frontend tests, gateway/contracts harnesses,
generated types, Next typegen, TypeScript, lint, build/post-build typing; container
and three Compose checks; `git diff --check` and final Git/migration audits. Record
all exact results and limitations in `docs/architecture/any-640-verification.md`.

## Handoff

Update `docs/architecture/ownership.md`, `docs/architecture/any-640-verification.md`
and ignored `AGENT.md`. Report files by layer, ownership, verification and limits.
Deployment, live-provider verification, retirement of unrelated legacy TypeScript
helpers and full Slice G browser journeys remain follow-ups. Leave the complete
Slice F work uncommitted.

## Execution ledger

2026-10-10: Required branch and committed Slice E HEAD confirmed. Index empty; only
the four named untracked files exist. Required docs, existing TS handlers/callers/tests,
Drizzle schema, Python contracts/UoW/repositories and current OpenAPI inspected.
Ruling: skip executing-plans commit steps because the user explicitly forbids commits;
the plan file and verification record carry the durable execution evidence.

2026-10-11: All four operations cut over. Full backend, frontend compatibility,
contract, static, build, container and Compose gates pass; exact evidence is in
`../any-640-verification.md`. Container verification now separates connected
forwarding from an explicit backend outage. Final Git/migration audit and read-only
review complete the handoff; changes remain uncommitted as required.

2026-10-11 review follow-up: Correct the evaluation request OpenAPI to model the
three accuracy variants exactly, regenerate both contract artifacts, add generated-
type regressions, and remove the retired TypeScript evaluation implementation only
after an import audit. Preserve runtime parsing/error order and all unrelated work;
run the user-specified focused checks without dependency installation.

2026-10-11 review follow-up complete: The OpenAPI request is a three-branch `oneOf`;
generated TypeScript requires `humanVerdict` for `wrong` and types it as `never` for
`correct`/`debatable`. Python contract and TypeScript compile regressions pass. `rg`
found only the obsolete evaluation unit tests importing the retired modules, so the
three production modules and those duplicate tests were removed. Focused backend,
OpenAPI, Ruff, mypy, generated-type, gateway and TypeScript checks pass; no commit or
push was made.
