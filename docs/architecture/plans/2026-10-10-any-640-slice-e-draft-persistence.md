# ANY-640 Slice E — FastAPI draft persistence

Approved in chat on 2026-10-10. Execute inline with executing-plans and
test-driven-development; retain this plan as the execution ledger.

**Issue/goal:** ANY-640; transfer GET/POST /api/drafts and GET/PUT
/api/drafts/{id} to Python while preserving contracts and historical data.
**Starting HEAD:** a474d0ec57b5143aca9b8de296dffb6b99f5eccf (committed Slice D).
**Branch:** codex/any-640-fastapi-business-workflows.
**Base:** ANY-639 97518baacaba56a1a2542fe145b14d62644c5fda.
**Checkout:** approved current checkout; no worktree, branch change, staging,
commit, push, PR, deployment, application database mutation or migration changes.
Preserve .gitignore, dev.sh, docker-compose.override.yml, pnpm-workspace.yaml,
test_openai.mjs. AGENT.md remains ignored.

## Architecture and interfaces

Python owns draft authentication, validation, proof verification, owner-filtered
reads, creation/retries, updates and serialization. Next retains UI/navigation
and forwarding. History POST, evaluations and locale remain TypeScript-owned.
Drizzle remains sole migration authority. No pricing, prompts, PDF or product
rules change. Generation must continue reading Python-persisted drafts.

Frozen/slotted document, reply, project-details, editable-change-order, creation
command, stored draft, summary and outcome values cross all ports; reuse Slice D
analysis/materials/replies/labels. Collections are tuples. Historical project and
analysis payloads use immutable wrappers around recursively typed frozen JSON,
preserving missing/null/legacy values without read normalization. ORM rows and
temporary dictionaries remain boundary-local; serializers allocate fresh JSON.

DraftRepository exposes owned list/detail, owned-project lock, owned creation-key
lookup, history/draft insertion, lastChecked update and editable-document update.
DraftWork wraps existing SQLAlchemy UoW, exposing repository and explicit commit.
DraftService.list/get/create/update inject work factory and clock. Creation takes
verified immutable input. Update takes an asynchronous document-reader callback
so resource lookup precedes body validation without leaking HTTP/decoded JSON.
Adapters flush, never commit; final updates and retry queries filter ownership.
Existing Slice D historical read protocol remains compatible.

Wire paths/camelCase/envelopes remain unchanged. OpenAPI documents 201 and retry
200 plus precise failures/cache. Preparatory schemas need compatibility fixes,
not use as automatic runtime validators that reorder validation.

## Ordered execution

- [x] 1. Freeze compatibility vectors and implement immutable values/parsing.
- [x] 2. SQLAlchemy repository/UoW and draft orchestration.
- [x] 3. Routes/contracts, grouped gateway cutover, retire TS persistence.
- [x] 4. Full verification, review, ownership/evidence/ignored handoff.

### Compatibility and parsing

Freeze TS-derived draft vectors before retiring parsers. Original 21-operation
corpus stays unchanged; annotate approved read-error cache addition explicitly.
Envelope/document limits count JSON.stringify UTF-8 bytes (inclusive 1,000,000),
including submitted unknown properties before discard, not raw body bytes.
Preserve UTF-16 lengths, JS trimming/string/number/date semantics, required-nullable
fields, language/labels, empty editable strings, optional reference and restricted
aiValues; 100000 text and 1500 label limits apply exactly where legacy applies.
IDs require hyphenated hex UUID syntax, case-insensitive. Retain textual project
ID through exact proof binding, then convert UUID. Normalize candidate protected
analysis fields and compare against verified/stored values with absent/null
distinction. Editable replies/commercial/language/labels stay editable.

### Persistence

Reads join owned projects/history. List orders created_at DESC,id DESC; project
name SQL COALESCE(snapshot name, editor name,current name) preserves empty strings.
Preview retains <=160 UTF16 units, otherwise first 157 + ellipsis, including lone
surrogate boundary. Read work closes/rolls back without commit.

POST validates envelope/proof/document before write work, locks owned project
FOR UPDATE, then looks up (projectId,idempotencyKey). Valid retry returns original
pair unchanged even for a different document. Invalid/expired proof fails first.
New save inserts one history and linked draft, updates lastChecked and commits
once; one clock instant produces UTC date and both draft timestamps. Existing
unique index plus project lock serializes concurrent requests to 201/200 and one
pair. No uniqueness retry loop. Verified snapshots alone supply historical data.

PUT loads owned draft before body validation within one work; uses saved locale
and analysis. Updates only document, derived language/labels, updatedAt; reloads
inside work and commits once. Never modifies snapshots/request/history/createdAt,
key/locale/request-language/project scope/lastChecked. Last-writer-wins unchanged.
Failures/cancellation roll back/close through inherited work lifecycle; failures
before commit leave no partial state. Lost committed response uses idempotency.

### HTTP and frontend

Origin protection precedes mutation processing; authoritative auth precedes IDs.
POST: auth -> object/envelope size/fields -> Slice D proof -> document -> lock
-> retry/create. PUT: auth -> ID -> owned lookup -> body/document -> update.
GET malformed/missing/foreign all 404/errors.draftNotFound. Bad body 400/requestBodyInvalid;
proof 400/draftProofInvalid; project 404/projectNotFound; reads 500/draftLoadFailed;
persistence 500/draftSaveFailed. No 422/detail. All draft GET responses, including
auth/resource/DB errors, have Cache-Control private,no-store (approved choice).
Narrow response-header middleware includes dependency failures. UTC millisecond Z
timestamps, surrogate-safe JSON, unchanged draft/list/history/projectId/draftId.

Two Next route files forward once through existing gateway: raw method/body,
Cookie/Origin/cancellation/status/headers; no retry/fallback. GET gateway-generated
503/requestFailed gets private cache too. Delete production TS persistence; move
verifier/validation references to tests, retain browser builders/types/editor.
Persistence tests use disposable Python gateway with real synthetic sessions and
actual draft URLs. Regenerate OpenAPI/types; add drafts-gateway harness suite.

## Test matrix and commands

Unit: deeply immutable/detached values, validation precedence, UTF8/UTF16 limits,
omitted/null, nested/date/language/label vectors, protected fields and metadata.
API/proof: expiry/issuer/audience/version/algorithm/key/subject/bindings/session
rejection, auth/Origin precedence, exact statuses/errors/headers, malformed resources.
PG: two owners, tied-date ordering, concurrent 201/200 one pair, changed-document
retry, failures after history/draft/project update and commit, immutable PUT,
legacy/null snapshots, ownership on mutation. All drafts paths zero LLM calls.
Contracts: original corpus + draft vectors, exact links/dates/omission/headers,
four OpenAPI operations/type freshness. Frontend: forwarding/raw body/outage/no TS
DB imports, first save/edit/reload/history/deep links/lost response/stale UI/languages.
Deterministic doubles and owned disposable PG only; infra failure is failed gate.

Backend cwd:
```text
uv run --no-sync pytest tests/unit tests/api -q
uv run --no-sync pytest tests/integration --require-integration --basetemp .pytest_cache/any640_e_integration -q
uv run --no-sync pytest --require-integration --basetemp .pytest_cache/any640_e_final -q
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy src/scope_guard
uv run --no-sync python scripts/export_openapi.py --check ../contracts/openapi.json
```
Frontend cwd (synthetic configuration):
```text
corepack pnpm api:types:check
corepack pnpm exec next typegen
corepack pnpm exec tsc --noEmit
corepack pnpm lint
corepack pnpm build
corepack pnpm exec tsc --noEmit
node --test scripts/docker-entrypoint.test.mjs
```
Root:
```text
node scripts/verify-any640.mjs --suite frontend
node scripts/verify-any640.mjs --suite contracts
node scripts/verify-any640.mjs --suite drafts-gateway
node scripts/verify-any640.mjs --suite generation-gateway
node scripts/verify-any640.mjs --suite containers
docker compose -f compose.yaml --profile app config --quiet
docker compose -f docker-compose.yml --profile app config --quiet
docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet
git diff --check
git diff --cached --check
git status --short --branch
```

## Rollback, evidence and limitations

Document backend-first rollout, drain draft writes then grouped frontend switch.
Rollback prior compatible image pair; no schema reversal/fallback. Sanitized
status/error/latency evidence only; never content/cookies/proofs/credentials.
Update ownership.md, any-640-verification.md and ignored AGENT.md (stale D state).
Final report: files grouped by layer, exact ownership, transaction/idempotency,
commands/results/limitations and uncommitted E/unrelated preservation confirmation.
D image gate previously failed npm downloads; rerun, do not claim historical pass.
Deployment/live-provider/full Slice G browser journeys remain follow-ups.

## Execution ledger

2026-10-10: Branch/HEAD and empty index confirmed; only named unrelated changes.
Root/frontend AGENTS, plan README, main/D plans, verification, ignored AGENT and
installed Next route-handler guide read during planning. Plan approved in chat.
Ruling: use this approved plan as ledger; no skill worktree/commits or extra
spec document because user explicitly forbids those operations.

Red/green: 10 unit/API tests failed for absent parser/routes, then 13 focused
unit/API/disposable-PG tests passed. Two forwarding tests failed on TS DB imports,
then gateway and verifier-reference tests passed. Frozen TS document vectors
are shared by both runtimes. Full frontend: 335/43 plus 19 Python contracts passed.
PG integration: 27 passed, including deferred commit failure after all writes.
Initial unit/API run: 308 passed; stale route-inventory assertion and two inherited
global pytest temp-access errors. Inventory updated; final commands use owned
basetemp and UV_CACHE_DIR because the default Windows cache is inaccessible.
Final reviewed backend: 344 passed in 87.37s (317 unit/API + 27 integration).
Final frontend: 336 tests/44 files in 18.02s plus 19 contracts. Contracts,
drafts-gateway and generation-gateway passed; gateway journeys cover 15 auth and
14 project checks. Ruff, format (138 files), mypy (72 sources), OpenAPI/types,
TypeScript before/after production build, lint, entrypoint (3), all three Compose
configurations and diff checks passed. Existing lint/Vite/Starlette warnings remain.
Independent reviewer reran 33 tests and reported no Critical/Important findings.
Review regressions fixed legacy date parsing, encoded slash-ID handling and deep
JSON error mapping; OpenAPI now describes optional non-null fields/cache headers.
Full verification commands/results, environment adaptations and rollout evidence:
../any-640-verification.md, Slice E. Both container images built and 10 HTTP smoke
checks passed, closing Slice D's previous failed gate. The first smoke run exposed
an inherited unauthenticated-generation assertion and draft proxy interception;
the assertion is corrected and draft APIs delegate authentication to Python after
Origin protection. A failing/passing four-method regression and independent
review cover the correction. Concurrent frontend proof-interop timeout passed on
the final isolated full rerun; no timeout adjustment. Registry downloads were slow
but completed. All intermediate failures and adaptations are in the evidence.
Ownership and ignored handoff updated. HEAD unchanged, index empty; no unrelated
file edits or schema/migration changes. Deployment/live providers/full Slice G
browser journeys remain follow-ups, not part of this authorization.
