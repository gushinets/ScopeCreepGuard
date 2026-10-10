# ANY-640 Slice D — generation, OpenAI, and draft proofs

Approved by the user in chat on 2026-10-10 for implementation in the current
checkout. This record implements the detailed five-section plan approved in chat.

**Branch:** codex/any-640-fastapi-business-workflows.
**Starting HEAD:** 5068724db1f89c999c6aac6b60c5aa2b0129bcad.
**ANY-639 base:** 97518baacaba56a1a2542fe145b14d62644c5fda.
Slice C and its immutable-value correction are reviewed and committed at this HEAD.
Preserve unrelated local files. No branch changes, staging, commits, pushes, PRs,
application database operations, schema changes or deployment in this task.

## Ownership and boundaries

Python owns POST /api/analyze, /api/replies/regenerate,
/api/client-materials/language and /api/change-orders/estimate together. Next
handlers only forward through the existing gateway, once, without fallback or
retry. Generation writes no project, history, draft or evaluation. Drizzle retains
migration ownership; draft saving and its TypeScript proof verifier stay through E.

Frozen/slotted domain inputs/results and tuple collections cross ports. HTTP
parsing/errors/serialization live in api; orchestration in modules; persistence
in infrastructure/database/repositories; provider access in infrastructure/llm.
Close the read UoW before OpenAI, including retries; no connection/lock survives.

## Compatibility contract

Port exact runtime strings from llm/prompt.ts, reply-tone-skills.ts and
llm/client-materials.ts, plus exact provider schemas. Freeze them before cutover.
Preserve warm/neutral/firm, verbatim citations, interface-language analysis,
client/request-language replies/CO/labels and neutral-request locale fallback.
Keep broad BCP47 reply/model languages and separate existing PDF restrictions.
Preserve omitted/null, JS trim/UTF16/JSON semantics, optional result normalization,
request validation order, responses/errors/status/cache headers and cookies.

Validation after auth:
- Analyze: object/language/id/request/date, owned project/date/scope, allowance,
  combined size, locale, generation/snapshot/proof.
- Reply: object/language/id/request/tone/previous/individual size, owned
  project/scope/combined size, allowance, locale, generation.
- Materials: object/types/language/serialized size, owned project/history request,
  locale/historical context, analysis/history verdict+summary/effective size,
  allowance, translation.
- Estimate: object/types/nonblank request/date/language, owned project,
  locale/historical context/date/complete terms/size, allowance, generation/guards.

Analyze/reply trim; materials preserve request; estimate budgets raw request then
generates trimmed request. Budget 100000 UTF16 units. Invalid project UUID is
500/requestFailed; invalid historical context 400/draftProofInvalid. No 422/detail.
Only analyze success is private,no-store. Locale defaults ru; invalid cookie throws.

draftId precedes proof, then current context. Owned drafts bind project and exact
request. Null historical snapshots use empty scope/null terms, never current
terms. Preserve legacy display/client fallbacks and snapshot overlay semantics.
Body locale binds proofs, not interface output. No new full-analysis equality check.

Keep model-driven hourly/fixed pricing, project currency, complete-term guards,
UTC calendar timing/Date.UTC behaviour and explicit-vs-draft end boundary. Signature
is JSON [pricingModel,currency,hourlyRate,fixedPrice,startDate,endDate-or-empty].
No new formula. Estimate included/no-extra is 409/analysisInvalid; bad estimate or
currency mismatch 502/analysisInvalid. Analyze flags currency mismatch invalid.

## Provider, proofs and failure behaviour

gpt-5.4-nano nonstreaming Responses instructions/input; reasoning medium except
reply high. Strict scope_analysis/client_materials schemas unchanged. No new
temperature/token/tools/conversation/background/store policy. Official async SDK
is locked; nested retries disabled, one adapter retry owner preserves JS behaviour:
two retries for connection/timeouts, 408/409/429/5xx, x-should-retry precedence,
retry-after-ms then numeric/date Retry-After, else min(.5*2^n,8)*(1-random*.25).
No new server-delay cap. Per-attempt 600-second deadline; no shorter gateway or
total deadline. No retries of cancellation/invalid output/business guards.
Missing key 503/analysisUnavailable; invalid JSON/shape 502/analysisInvalid;
provider/incomplete/empty analysis/reply 502/analysisFailed. Materials classify
completion/parsing/applicability failures invalid, provider exceptions failed.
Otherwise 500/requestFailed.

Proof HS256 typ/version scg-draft-proof-v1, issuer scope-creep-guard, audience
draft-creation; sub/userId bind user, project/request/locale exact. Key is
HMAC-SHA256(auth-secret UTF8,version UTF8). Issue integer iat/exp, lifetime 3600s;
verify original segments, expiry/no future iat/positive duration<=3600/nbf/required
claims/version1 snapshot/UUID and 2000000 UTF16 token limit. Sessions cannot act
as proofs. No individual-session nonce. TS saver still verifies Python proofs.

One app-scoped limiter: 10/user/rolling60000ms, timestamps strictly newer than
window start; synchronous atomic admission, one worker/replica, no refunds.
Cancel/await workflow after disconnect and body consumption; shield UoW cleanup;
no new 499 or automatic replay. Correlation UUID and sanitized event/status/type,
duration/attempt/token/provider-ID fields only. Never content/credentials/proofs.

## Ordered execution and evidence

- [x] 1. Save plan/handoff, preserve checkout state.
- [x] 2. Freeze TS prompts/schemas/normalization/validation/languages/proof vectors.
- [x] 3. Immutable domains/parsers/normalization/read ports/historical resolver.
- [x] 4. Proof/OpenAI/retry/limiter/cancellation/logging infrastructure.
- [x] 5. Four Python workflows/routes and generated contracts.
- [x] 6. Python proof -> unchanged TS saver -> reload/concurrent deduplication.
- [x] 7. Grouped four-handler forwarding and gateway/harness cutover.
- [x] 8. Retire TS production generation/issuance, retain saver/browser helpers.
- [x] 9. Full verification, evidence/ownership/handoff; stop for review.

Tests: unit input/normalization/immutability/context/prompts/adapter/retry/rate/
proofs/timing/JS; all-four API guards; real PostgreSQL owner isolation/no writes/
pool return/cancellation/history; bidirectional JOSE and transitional saver;
frontend exact forwarding/outages/edit/stale/history/language/estimate behaviour;
unchanged 21-operation corpus plus generation vectors; OpenAPI/types/containers.
Matrix EN/RU UI x RU/EN/ES/DE/pt-BR/es-419/neutral, all tones/broad reply scripts,
aliases/unsupported scripts, hourly/fixed/currencies/dates, historical/null/client
snapshots, malformed output, every proof boundary, mixed-route rate/concurrency,
zero or one logical call, private-content log sentinels and frontend outages.
Use deterministic provider doubles and owned disposable DBs only. Required infra
failure fails verification. Full pytest/integration/Ruff/format/mypy/OpenAPI,
frontend tests/lint/types/build, contracts/gateway/containers/Compose/diff checks.
Exact evidence belongs in ../any-640-verification.md; no invented passing counts.

## Rollout, limitations and follow-ups

Deploy compatible backend first with shared auth/database/OpenAI/proxy config,
one worker/replica. Stop all-four admission, drain old work, wait a rolling-minute
quiet window, deploy all-four frontend forwarders/remove frontend OpenAI config,
reopen and verify generation+TS save. Rollback previous frontend/backend image
pair and configuration with the same drain; no per-request fallback/schema reversal.
Actual deployment is not authorized here.

No new product behaviour approved. Model/prompt/pricing/timeout/retry/language/
session-binding/distributed-limit/historical-reply changes require separate approval.
Risks: JS/Python JSON+Unicode+date semantics, locale/language ordering, legacy
normalization/snapshots, retry timing, secret alignment, limiter reset, TS saver
interoperability and recorded transient harness load failure. E owns draft writes;
F remaining APIs; G final retirement/full browser journeys. AGENT.md stays ignored.

## Execution ledger

2026-10-10: Preconditions rechecked; HEAD/branch unchanged; only identified unrelated
local files present. User-approved current checkout overrides skill worktree default.
No automatic commits. Plan is the execution ledger while changes remain uncommitted.

Implementation and independent review corrections complete; user authorized one
local Slice D commit. Final backend 307 tests and frontend 341/42 plus 19 contracts
passed. Production gateway, static checks and native build passed. Container image
verification remains an explicit deployment gate because frontend dependency
downloads timed out twice. Exact evidence is recorded in
../any-640-verification.md. No deployment or push.

Technical layout consolidation: analysis workflows share GenerationUseCases;
the draft read protocol is in analysis.ports; pure serialization is shared beneath
modules.analysis, with API generation_output re-exporting it. Responsibilities
and immutable boundaries remain as approved.
