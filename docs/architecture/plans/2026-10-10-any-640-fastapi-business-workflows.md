# ANY-640 — Next.js API and business workflow migration

> Approved in chat on 2026-10-10. Use Superpowers executing-plans and test-driven
> development, one reviewed slice at a time. Stop after each slice for review.

**Issue:** ANY-640, Migrate the existing Next.js API and business workflows to Python/FastAPI.
**Spec:** https://linear.app/paveldik/issue/ANY-640/migrate-the-existing-nextjs-api-and-business-workflows-to
**Goal:** Move all 21 existing business API operations to FastAPI while preserving frontend journeys, data, contracts, and product rules.
**Branch:** codex/any-640-fastapi-business-workflows.
**Exact base:** origin/codex/any-639-data-contracts-and-alembic at 97518baacaba56a1a2542fe145b14d62644c5fda, fetched and inspected before branch creation.
**Checkout workflow:** Approved current checkout; necessary child-branch switch reviewed in the plan and performed after approval. Preserve unrelated changes. No automatic commits or pushes.
**Architecture:** One public origin and unchanged /api paths. Next.js forwards each migrated operation to Python; operations awaiting migration retain their TypeScript owner. SQLAlchemy repositories and use cases own migrated persistence/business logic. Drizzle retains migration authority.
**Stack:** Next.js 16.3; Python 3.12; FastAPI/Pydantic 2; async SQLAlchemy/Psycopg; PostgreSQL 17.

## Baseline and global constraints

- Planning HEAD and independently queried remote HEAD were 97518baacaba56a1a2542fe145b14d62644c5fda. ANY-638 ancestor: 9d317c391254ae06424c195536ab94e437d9cb3c. Parent includes data foundation, inherited port/language fixes and normalized provenance hashes.
- Inspected root/frontend AGENTS.md, ignored AGENT.md, plan README, complete Linear ticket/comments, current routes/tests/callers, Python contracts/models/UoW/Alembic/tests, deployment and installed Next.js guides. Stage 1 was read-only; no tests were claimed as freshly passing.
- Preserve modified .gitignore and untracked dev.sh, docker-compose.override.yml, pnpm-workspace.yaml, test_openai.mjs. Stage only ANY-640 files when separately authorized.
- No reset, clean, stash, application-database mutation, history rewriting, automatic commit/push or PR-base changes. Disposable verification databases only. Explicit review before commits/pushes/rebase/PR-base changes.
- No microservices, Redis/queues by default, UI redesign, new pricing/model policy, schema redesign, event tracking, PDF/extraction/currency migration or migration-authority transfer.
- Plan approval starts implementation; subsequent slices require review of the preceding slice.

### Approved choices

| Decision | Selected behavior |
|---|---|
| Checkout | Current checkout, child branch from freshly fetched ANY-639 |
| Locale | FastAPI owns the existing locale cookie operation |
| Legacy history | Retain unchanged; never call automatically after analysis |
| LLM deployment | One worker and one replica; all four LLM routes switch together |
| Unexpected failures | Otherwise unmapped exceptions become 500/errors.requestFailed |
| Origin protection | Supplied origins outside configured public-origin allowlist become 403/errors.requestFailed; origin-less server clients allowed |

### Reconciled ticket gaps

- The older-checkout warning is historical: this parent contains project management, drafts, signed proofs and immutable snapshots.
- ANY-639 has schemas/domain helpers, five table mappings, explicit transaction lifecycle, guarded baseline and two health routes; no business routes, repositories or auth/LLM adapters.
- Existing Python schemas are preparation, not HTTP parity: reconcile nullability, aliases, normalization, field limits and JS semantics using fixtures.
- Draft POST entry includes projectId and draftId; project history reads and legacy history POST omit projectId.
- Full-card PATCH preserves clientName when omitted; null clears it.
- Evaluation labeling captures current project scope/industry, stored history request/verdict and caller reasoning; relabeling replaces evaluation context. Do not change provenance.
- Reply regeneration uses current project; material language and estimation support historical draft/proof context.
- Origin checking and generic JSON 500 fallback are approved additions. Concurrent registration uniqueness maps to ticket-required duplicateEmail 409.
- E2E currently has only a README; add executable coverage. Add backend static type checking.
- Drizzle remains migration owner. No Alembic adoption on application databases.

## HTTP inventory and compatibility contract

JSON success/error responses use application/json; explicit errors are exactly {"error":"errors.<code>"}. Preserve ignored unknown properties, validation order, trimming, omitted/null distinctions and endpoint limits. Except register/login/logout/locale, operations require signed session plus existing DB user: missing auth is 401/authRequired. Foreign resources are indistinguishable from missing.

Only auth/locale set cookies. Successful analyze/draft-list/draft-detail have Cache-Control: private, no-store; other responses do not silently gain this header. Unmapped failures use approved 500/requestFailed. Approved Origin rejection runs before state-changing/LLM processing.

| Operation | Request / success | Failures / persistence | Caller |
|---|---|---|---|
| POST /api/auth/register | email,password -> 201 {user:{id,email}} | Normalize email; validate; bcrypt cost 12; insert user; session. 400 credential/body; 409 duplicateEmail, including concurrent uniqueness | Register auth form |
| POST /api/auth/login | email,password -> 200 {user} | Same validation; compare existing hash; session; 400 input, 401 invalidCredentials; no business write | Login auth form |
| POST /api/auth/logout | No body -> 200 {ok:true} | Public; expire session, Max-Age 0; no DB session | Workspace logout |
| GET /api/auth/me | Cookie -> 200 {user} | Token then DB user; 401 authRequired; no writes/renewal | Bootstrap |
| GET /api/projects | -> 200 {projects} | Owner-filtered; creation DESC, history date DESC; no writes | Bootstrap/list |
| POST /api/projects | Complete card -> 201 {project} | Insert owned project, empty history; 400 field codes; ignore browser email/endDate | New project |
| GET /api/projects/{id} | -> 200 {project} | Owned with history; 404 projectNotFound; malformed UUID may currently cause DB 500, not 422 | Retained API, no direct product caller |
| PATCH /api/projects/{id} | Complete card -> 200 {project} | Full-card validation; omitted clientName preserved, null clears; retain history; 400 fields, 404 missing/foreign | Edit project |
| DELETE /api/projects/{id} | -> 200 {ok:true} | Owned delete; 404; cascades linked history/drafts/evaluations; unlinked evaluations survive | Confirm delete |
| POST /api/projects/{id}/history | date,request,verdict,summary -> 201 {entry:{id,date,request,verdict,summary}} | Atomic history insert + lastChecked; 404 project; 400 body/historyDateInvalid/requestRequired/verdictInvalid/summaryRequired; legacy date parser checks format before DB calendar validation | No current product caller; retained |
| POST /api/analyze | projectId,request,endDate?,documentLanguage? -> 200 {result,projectSnapshot,proof} | Current owned project; 400 body/request/scope/language/input; 404,429; LLM failures; no writes; private/no-store | Analyze |
| POST /api/replies/regenerate | projectId,request,tone,previousReply,documentLanguage? -> 200 {reply} | Current context, selected tone; 400 body/request/scope/locale/input; 404,429,LLM; no writes | Client reply |
| POST /api/client-materials/language | projectId,request,clientLanguage,analysis,historyId?,draftId?,proof?,locale? -> 200 {materials} | Translate established material; validate owned history/request/verdict/summary; historical context; 400 body/language/input/locale/proof; 404,429,LLM; no scope reassessment/pricing/writes | Language selection |
| POST /api/change-orders/estimate | projectId,request,endDate?,documentLanguage?,draftId?,proof?,locale? -> 200 {result} | Historical context, complete terms; rerun analysis/estimate; 400 body/language/locale/proof/pricing/input; 404,429; 409 analysisInvalid included/no extra work; 502 analysisInvalid invalid estimate/currency; LLM failures; no writes | Estimate refresh |
| GET /api/drafts | -> 200 {drafts} | Owned summaries, createdAt/id DESC; historical name/preview; 500 draftLoadFailed; private/no-store | My drafts |
| POST /api/drafts | projectId,request,locale,idempotencyKey,proof,draftDocument -> 201 {draft,entry}, retry 200 | Envelope -> proof -> document; owned project lock; atomic history/draft/lastChecked or existing result; entry includes projectId/draftId; 400 requestBodyInvalid/draftProofInvalid; 404 projectNotFound; 500 draftSaveFailed; no LLM | First save |
| GET /api/drafts/{id} | -> 200 {draft} | Malformed/missing/foreign ID 404 draftNotFound; 500 draftLoadFailed; private/no-store | Open/history/deep link |
| PUT /api/drafts/{id} | draftDocument -> 200 {draft} | Stored locale/analysis validation; edit document/language/labels/updatedAt only; 404 draftNotFound,400 requestBodyInvalid,500 draftSaveFailed; no LLM/history | Subsequent save |
| POST /api/evaluations | historyEntryId,accuracy,aiReasoning,humanVerdict? -> 200 {evaluation:{id,accuracy,humanVerdict}} | Owned history + upsert; 404 evaluationHistoryNotFound for invalid/missing/foreign ID; 400 evaluationReasoningRequired/evaluationLabelInvalid/body; no LLM | Feedback |
| GET /api/evaluations/export | -> 200 JSONL | Owned evaluation records, createdAt/id ASC; exact headers/bytes; no writes | Export |
| POST /api/locale | locale en/ru -> 200 {ok:true} | Public; one-year cookie; 400 requestBodyInvalid/localeInvalid; no DB | UI language |

### Exact shared shapes and invariants

- Session: scg_session, HS256/AUTH_SECRET, sub/email/iat/exp, seven days. HttpOnly, SameSite=Lax, Path=/, Secure in production. No renewal in me. Password min uses JS length; bcrypt fixtures include UTF-8 72-byte truncation, Unicode, embedded nulls and prefixes.
- Card: name, optional clientName, industry Development/Design/Marketing, scope, valid YYYY-MM-DD startDate, pricingModel hourly/fixed, currency RUB/USD/EUR, active hourlyRate/fixedPrice. Current number/string inputs; positive <1e12, <=2 decimals; two-place decimal strings; inactive amount null.
- Project: id,name,clientName,industry,scope,startDate,pricingModel,currency,hourlyRate,fixedPrice,history; lastChecked omitted when absent. History id,date,request,verdict,summary, optional draftId. Legacy terms remain null. Browser clientEmail/endDate remain local; captured document/snapshot values supported.
- Analysis: verdict; confidence integer 0..100; summary/reasoning/citations; optional suggestion; warm/neutral/firm replies; changeOrder description,timelineImpact,additionalCost,note, optional estimatedHours/currency/rationale. Preserve hasAdditionalWork/requestLanguage/clientLanguage/labels/estimateValid/draftCreatedAt/commercialSignature, normalization and omitted empty suggestion.
- Materials: clientLanguage,replies, nullable changeOrder, optional labels. Translate description,timelineImpact,rationale,note only; preserve labels and all numeric/factual content.
- Snapshot: version 1, name, optional-null clientName, industry, scope, nullable terms, endDate/documentLanguage. Legacy SQL-null snapshots stay null.
- Draft v1: result, required-nullable clientMaterials/changeOrder, reply {tone,text,generated}, projectDetails {clientName,clientEmail,endDate}; all existing editor fields/reference/aiValues/labels, empty editable strings and amounts preserved.
- Saved draft: id,projectId,historyEntryId,request,createdAt,updatedAt,status,locale,requestLanguage,clientMaterialLanguage,projectSnapshot,analysisSnapshot,draftDocument. UTC millisecond Z timestamps. List items id,requestPreview,projectName,verdict,createdAt,updatedAt; JS preview slicing preserved.
- Evaluations: correct resolves to AI verdict, debatable null, wrong requires a different verdict. humanVerdict key prohibited for correct/debatable including null.
- JSONL: application/x-ndjson; charset=utf-8; attachment; filename="scope-creep-evaluations.jsonl". scope,request,ai_verdict,human_verdict,ai_reasoning,project_type. Uppercase verdicts, lowercase project types. Empty bytes for empty export; exactly final newline for nonempty export.
- Locale cookie locale: one year, not HttpOnly, SameSite=Lax, Path=/, production Secure. UI cookie/default ru, no request-body override. Invalid cookie matches resolver failure, not silent fallback. Saved locale governs draft updates.
- LLM failure mapping: missing key 503/analysisUnavailable; invalid JSON/analysis shape 502/analysisInvalid; other failures 502/analysisFailed. Preserve material adapter completion/parsing classification.

## Layers and gradual cutover

| Layer | Responsibility |
|---|---|
| api/routes | HTTP, parsing/dependencies, cookies/headers/wrappers, compatibility validation order and error mapping |
| modules/*/use_cases.py | Workflows, owner rules, generation context, immutable state, transaction orchestration |
| modules/*/repository.py | Typed persistence protocols returning application data, not ORM rows |
| infrastructure/database/repositories | Owner-filtered SQLAlchemy joins/mutations, locks, upsert, flush; no independent commits |
| Unit of Work | Separate session per workflow; explicit commit; rollback/close on errors/cancellation |
| infrastructure/auth | Bcrypt, session/proof adapters and separated keys |
| infrastructure/llm | Async OpenAI, exact prompts/schema/parsing/canonicalization, shared allowance |
| infrastructure/currency | Future server adapter boundary; no conversion migration here |
| Frontend API | Typed requests, existing error interpretation, same-origin forwarding/browser flows |

Use-case groups: Auth, Projects/History, Analysis/Replies/Materials, Change Orders, Drafts, Evaluations. Inject UoW factory, clock, password/session/proof/LLM adapters and limiter. Repository ports expose corresponding owned reads/mutations; draft creation exposes owned project lock and (projectId,idempotencyKey) lookup.

Add request/response schemas/wrappers for all operations. Public input is camelCase, strict and non-coercing; do not accept internal snake aliases accidentally. Generated OpenAPI documents implemented routes only and known failures. No default 422/detail reaches callers.

### Transport

- Browser keeps relative /api paths. Shared server-only Next forwarding helper; migrated handlers forward only their existing methods. Pending operations retain TS owner.
- Forward raw body/query/Cookie/Origin/content type/cancellation; preserve upstream body/status/relevant headers and individual Set-Cookie. Fixed server-configured backend origin; never caller-selected.
- Forward once; no proxy retry or TS fallback. Transport failure 503/errors.requestFailed; backend responses preserved.
- Consolidate browser request/error handling in frontend/lib/api across auth/workspace/replies/locale/export.
- Python authorizes APIs; Next lightweight session verification is navigation only. In B migrate deprecated middleware naming to proxy.ts and pass API traffic to selected owner.
- Stale/deleted-user sessions: authoritative me lookup, expire stale cookie and login navigation. Service failures recover without redirect loop.
- Completion: all 21 operations reach Python through transport-only Next handlers; no TS business fallback.

### Generation

- No business writes from generation; close read transactions before LLM, holding no locks/connections.
- Keep gpt-5.4-nano Responses JSON schema, reasoning medium for analysis/materials and high for reply, maxRetries 2. One logical adapter invocation; SDK retries retained, no second proxy/workflow call.
- Preserve installed SDK ten-minute per-attempt timeout; no shorter forwarding deadline. Cancellation propagated; sanitized logs/correlation.
- UI-language summary/reasoning/suggestion; client-language replies/CO/labels; neutral fallback; verbatim citations; existing supported tags/scripts/canonicalization.
- Reply tags retain broader normalization than PDF-supported analyze/estimate/material tags.
- Preserve hourly/fixed prompts, explicit end date vs draft calculation boundary, exact commercialSignature JSON array; no new formula.
- All four generation routes switch together; one-process 10/user/rolling 60-second allowance. Preserve endpoint validation/budget order and JS UTF-16 counts.
- draftId context precedes proof; legacy missing snapshot uses empty scope/null historical terms, never today's terms. Reply regeneration remains current-context.

### Proof and draft trust

- scg-draft-proof-v1 typ/version; HS256; issuer scope-creep-guard; audience draft-creation; one hour. HMAC-SHA256(version string, session secret) key derivation.
- Required integer iat/exp/sub, no future iat, valid duration/expiry; exact user/project/request/locale bindings. Verify original JWT segments, never reconstructed JSON. Sessions cannot act as proofs.
- Envelope/proof/document validated before DB; lock owned project; creation-key lookup; one history/draft/lastChecked commit. Valid retry returns original even if submitted document differs; expired proof fails before retry lookup.
- PUT edits document/language metadata only, never snapshots/history/createdAt.

## Ordered slices and review gates

Each slice: write failing tests, observe failure, minimum implementation, relevant checks, frontend consumption when routes migrate, slice review. Do not start next slice before review.

### A. Errors, fixtures, transport foundation

- [x] Freeze TS-derived compatibility cases in contracts/compatibility/any-640/ using synthetic users, fixed clocks, LLM doubles.
- [x] All 21 operations: request/normalized response/status/headers/cookies/selected validation order/persistence/logical LLM count. Symbolically normalize nondeterministic IDs consistently without masking links/money/omission/timestamps. Expand edge/validation matrices at each migration gate.
- [x] Backend error mapping, explicit object parsing, request/response wrappers; reconcile parent schemas using fixtures.
- [x] Approved Origin check and generic-500 envelope; annotate intentional baseline differences.
- [x] Shared client/forwarding infrastructure without business ownership changes.
- [x] Generate/check OpenAPI and reproducible frontend API types.
- [x] Slice-A follow-up: mandatory backend tests/Ruff/mypy/OpenAPI and frontend tests/TypeScript/build/API-type CI gates, including PRs into main and the ANY-639 parent. Current ignored handoff and exact verification evidence updated; no business cutover.

Gate: both runtimes consume shared fixtures; no 422 leakage; Origin tests pass; intentional differences explicit; no business ownership changes.

### B. Sessions/page guards

- [x] User repository/auth use cases/bcrypt/session/four auth routes; optional secret config with AUTH_SECRET compatibility and independent liveness.
- [x] Concurrent registration 409; cross-runtime cookies/hash compatibility.
- [x] Cut auth to Python; update guards/client; retire TS endpoint hashing/issuance; retain TS current-user lookup for remaining workflows and navigation verifier.

Slice B ruling: retain the TS current-user database lookup for still-TS business
routes through their later cutovers; retiring it now would remove their owner
checks. Retire auth endpoint hashing/credential/session issuance logic after real
gateway interoperability passes. Keep the shared session verifier needed by page
guards and signed-proof key access. Public-page redirects must confirm `/me`
through Python so deleted-user cookies cannot create a login redirect loop.
Freshly fetched remote parent remains 97518baacaba56a1a2542fe145b14d62644c5fda.

Gate: frontend register/login/me/logout; production/dev flags; expired/tampered/deleted user; no loops; authoritative DB user.

### C. Projects/history repositories/ownership

- [x] Project/history ports/adapters/use cases; five project methods and exact ordering/serialization.
- [x] Preserve omission, inactive price nulls, legacy terms/browser details; shared owned history reads.
- [x] Cut five methods; legacy history POST stays TS until F; remove superseded project business code after frontend consumption.

Implementation checkpoint: SQLAlchemy project/history adapters compose the inherited Unit of Work. Full PATCH checks ownership before decoding its body. Retain TS single-project serialization/owner helpers for pending generation and legacy history; remove only the superseded list query and route business handlers. Frozen parser vectors characterize actual Number/toFixed monetary behavior. Production gateway and disposable database checks cover frontend consumption, foreign owners, cascades and immutable snapshots. See the Slice C verification record; Slice D awaits review.

Gate: frontend create/edit/delete; two users; cascades/unlinked evaluations; unchanged snapshots; no schema changes.

Required architectural follow-up: replace the shallow frozen Project/card dict
with nested immutable typed values and immutable application/repository outputs.
See [the correction plan](2026-10-10-any-640-immutable-project-values.md).

### D. Generation/OpenAI/proofs

- [ ] Port exact prompts/tones/schemas/normalization/languages/timing/signature/estimation; async adapter and sanitized correlation.
- [ ] Proof adapter and historical resolver; introduce read-only draft repository before draft writes.
- [ ] Four generation operations; Python proofs accepted by still-TS saver and reverse fixtures.
- [ ] Drain prior owner; grouped four-route switch; one worker/replica. Remove TS server generation/proof issuance after frontend and save interoperability pass.

Gate: shared limits, no writes, one logical call, language matrix/historical context/output failure mapping, temporary analysis still savable.

### E. Draft persistence

- [ ] Draft list/detail/create/update ports/adapters; atomic save/UoW and document-only update.
- [ ] One-million-byte UTF-8 JSON, nested limits, UUID envelope, proof order, JS preview.
- [ ] Protected verdict/confidence/summary/reasoning/citations/suggestion/hasAdditionalWork/requestLanguage including absent/present distinctions.
- [ ] Cut four operations; move persistence regressions to Python integration before removing TS business modules.

Gate: concurrent 201/200 one pair; injected rollback no partial writes; no retry LLM; reload/reopen/edit immutable context; isolation/legacy snapshots.

### F. Evaluations/export/history/locale

- [ ] Evaluation ports/use cases and exact upsert/provenance; JSONL bytes/order/headers/Unicode/newline.
- [ ] Legacy history retained without product caller; Python locale cookie with SSR compatibility.
- [ ] Cut four operations and remove TS business code.

Gate: frontend labels/export; concurrent upsert/isolation; JSONL equality; legacy effects; analyze does not save; locale reload/SSR.

### G. Complete cutover/deployment/retirement

- [ ] All callers typed API/transport only; preserve browser editors/PDF/extraction/currency/localization/shared parsers.
- [ ] Import audit, remove unused TS DB/LLM/auth/proof business modules/dependencies.
- [ ] Retain Drizzle schema/migrations/config/dependencies in migration target; frontend runner no DB/OpenAI requirements.
- [ ] Python config for DB/auth/OpenAI/proxy/origins in tracked entrypoints; untouched unrelated local override.
- [ ] Executable Playwright, mandatory CI including parent PR target; ownership/cutover/rollback/evidence docs.

Gate: 21 Python operations, full journeys, no frontend business credentials, production-shaped containers/generated contracts.

After each implemented slice update ignored AGENT.md with factual branch/base/current commit, completed slice, ownership, exact checks/results, risks/next slice; no secrets/personal paths/certificates/env values.

## Tests and verification

| Level | Scenarios |
|---|---|
| Unit | Validation order/types/trim/omission/nulls/JS JSON/string semantics/money/domain/language/prompts/estimation/signatures/rate/proof/session/password |
| API | All methods success/errors; malformed JSON/scalars/arrays; auth before processing; tokens/foreign resources/Origin/wrappers/headers/cookies/no 422 |
| PostgreSQL 17 | Real adapters/UoW; registration race; drafts concurrency/rollback; upsert/owner mutations/cascades/snapshots/cancellation/pool return |
| Cross-runtime | Bidirectional sessions/proofs, synthetic bcrypt, Unicode/72-byte edges, expiry/binding/key/typ/issuer/audience/separation |
| Contracts | Shared 21-method fixtures, status/body/headers/cookies, implemented OpenAPI coverage/type freshness, JSONL bytes |
| Frontend | Existing components/stores + client/proxy; stale results/edited values/deep links/unavailable drafts/languages/outages |
| Containers | Independent live/ready; forwarding/cookies/private cache/config failure/one generation process/no frontend business credentials |
| E2E | Register/login/project CRUD/analyze/all tones/client language/estimate/save/reload/reopen/edit/historical context/PDF/evaluation/export/delete/logout/two users |

EN/RU UI with Russian/English/Spanish/German/regional and neutral requests; legacy projects/drafts, missing resources, proof expiry, retries, backend outage. CI deterministic doubles; live model smoke separate/manual.

Backend commands (backend cwd):

```text
uv sync --locked --python 3.12
uv run pytest tests/unit tests/api
uv run pytest tests/integration --require-integration
uv run pytest --require-integration
uv run ruff check .
uv run ruff format --check .
uv run mypy src/scope_guard
uv run python scripts/export_openapi.py --check ../contracts/openapi.json
```

Add locked mypy dev dependency/configuration. Frontend commands (frontend cwd, owned disposable process config):

```text
corepack pnpm install --frozen-lockfile
corepack pnpm test
node --test scripts/docker-entrypoint.test.mjs
corepack pnpm lint
corepack pnpm exec next typegen
corepack pnpm exec tsc --noEmit
corepack pnpm build
corepack pnpm exec tsc --noEmit
corepack pnpm run api:types:check
corepack pnpm run verify:change-order-pdf
```

Add api:types:check comparing generation to committed OpenAPI. Root commands:

```text
docker compose -f compose.yaml --profile app config --quiet
docker compose -f docker-compose.yml --profile app config --quiet
docker compose -f docker-compose.dokploy.yml config --no-interpolate --no-env-resolution --quiet
docker build -t scope-guard-backend:any640 backend
node scripts/verify-any640.mjs --suite contracts
node scripts/verify-any640.mjs --suite containers
node scripts/verify-any640.mjs --suite e2e
git diff --check
git diff --cached --check
git status --short
```

Harness owns volume-free PG/unique DBs/processes/test LLM; synthetic process config, no local app env files, refuse external DB targets, cleanup verified owned resources only. Frontend container uses disposable build config. Root E2E specs use frontend locked Playwright dependency. Record exact commands/exit/counts/skips/limitations per slice; mandatory infrastructure failure must not silently skip coverage. Commands for later deliverables run when applicable, not fabricated in A.

## Rollout, rollback, and approvals

1. Fetch/inspect parent after approval; record exact head; materially changed base requires revised review. Create reviewed child preserving local changes. Save approved plan before source work.
2. Existing Drizzle gate/schema retained; no application migrations/adoption.
3. Deploy compatible backend before frontend slice; drain LLM owner before grouped D switch.
4. Rollback via previous frontend/backend image pair; never per-request TS fallback, reverse schema or repeat generation.
5. Record ownership; sanitized status/error rates/latency/readiness/correlation. Never log documents/prompts/cookies/proofs/credentials.
6. Interim PR remains stacked on ANY-639. After merge, reviewed rebase onto resulting origin/main before final PR or merge.
7. Commits/pushes/PR-base changes/rebase need concrete review. New multiprocess limiting, session rotation/logout, pricing/model policy, historical replies, partial PATCH, history removal, provenance, PDF/extraction/currency, schema/migration authority or analytics need further approval.

Verification evidence: docs/architecture/any-640-verification.md. Follow-ups: B sessions, C projects, D generation, E drafts, F remaining APIs, G retirement/deployment. Migration completion requires frontend consumption, not merely Python handlers.

Implementation ruling, slice A: executable route inventory establishes 21 operations across 16 files. The ticket and initial reviewed plan incorrectly said 22; coverage uses current code and adds no invented endpoint.
