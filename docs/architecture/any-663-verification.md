# ANY-663 verification and rollout

Implementation date: 2026-10-14 Europe/Moscow. Branch:
`codex/any-663-llm-workflow`, based on the approved integration commit `120b0cf`.
The current checkout was used without a worktree. The
[implementation plan](plans/2026-10-13-any-663-llm-workflow.md) records the agreed
scope and execution decisions. No push, PR, Linear status change or application
database migration is part of this work.

## Implemented behavior

An authenticated, keyed command freezes server-owned project/request, source
Draft revision, commercial values, historical analysis references and language
selection. Admission commits before returning `202`. A separate LLM worker scans
PostgreSQL at startup and every two seconds; HTTP disconnects and status polling
do not execute or cancel the work.

The worker accepts analysis in the interface language, then concurrently accepts
three complete replies and applicable Change Order text in the client language.
The backend assembles the existing successful result envelope. Accepted stages
are persisted and reused; no partial client materials are published on failure.
New checks never receive earlier replies/manual edits. Historical regeneration
uses the saved check's scope and accepted analysis. Estimate refresh retains that
scope/verdict while using current saved commercial values through the existing
estimate run. History remains immutable; explicit confirmed restoration reuses
the existing Draft and revision checks.

All enabled workflow generation, including the four legacy adapters, traverses
the same ProviderGateway. PydanticAI's custom `GatewayResponsesModel` passes
`NativeOutput(strict=True)` through LiteLLM Responses as native JSON Schema,
including medium/high reasoning settings. Corrections carry concrete validation
feedback back through the gateway; prompt-only JSON and FunctionModel are not
used. Pins are LiteLLM 1.89.3, PydanticAI slim 2.2.0, Pydantic 2.13.4, OpenAI
2.43.0, and Lingua 2.1.1. The uv lock contains the resolved dependencies.

The gateway owns at most two transport attempts per semantic attempt. The SDK and
HTTP-client retry paths are disabled. Each stage has three semantic attempts.
Default operation limits are 12 calls/check, 8/translation, 6/regeneration and
6/estimate; 180 seconds from admission; at most 60 seconds/call; 32,768 conservative
input tokens and 4,096 output tokens/call. The money envelope defaults to USD 1.00
and is frozen at admission.

## Recovery and accounting

The worker claims with a 90-second database lease and increasing epoch, renewing
every 15 seconds. Loss of renewal cancels local work. Dispatch, accepted-stage
writes and publication enforce epoch/lease/deadline/budget. Shutdown stops claims,
allows 30 seconds to drain, then cancels and records uncertain dispatches where
possible. Restart loads persisted inputs, prepared native requests, returned
candidates, counters and accepted stages within the original deadline/budget.
Publication rollback retains stage outputs and call accounting.

The additive Alembic revision `0005_llm_workflow` follows `0004_workflow_retire` and
adds only `llm_operations`, `llm_steps` and `provider_calls`. No applied migration
was rewritten. Money columns are `NUMERIC(20,10)` and calculations use Decimal.
The catalog check detects incompatible schema drift. Downgrade refuses to erase
provider accounting; use forward corrections and retain the tables on rollback.

Before dispatch, a separate transaction reserves an upper bound and consumes a
physical attempt. Reported, tariff-estimated and unresolved reserved amounts are
distinct. Missing reported cost/usage stays NULL; SDK defaults are not billing
data. Rejected outputs are included. Unknown timeout/crash outcomes retain their
reservation and consume an attempt; another attempt needs another reservation.
An observed amount exceeding a call's bound stops the operation even if its
overall money ceiling has room. Late accounting may reconcile that call but
cannot publish stale content. This does not establish exactly-once external
execution or a guarantee of the provider's invoice.

Admission requires a versioned local tariff or explicit conservative input/output
rate bounds in USD per token. The transport is direct OpenAI Responses, without
provider/model fallback. Operators must ensure the bound covers the configured
model and any returned model alias, cached/reasoning billing and the operation
window; fixed fees or unsupported billing/token behavior require refusal rather
than an assumed zero. Unknown pricing without a usable bound returns a persisted,
keyed `503 errors.providerBudgetUnavailable` before any call. The accounting
ceiling includes unresolved/concurrent reservations, not only known cost.

## API and frontend transition

Enable the new API, worker and frontend together. While the LLM workflow is
enabled, legacy generation requires an owned `draftId`, `expectedRevision` and a
stable UUID in `operationId` or `Idempotency-Key`. Missing keys return 428,
inconsistent keys return 400, changed parameters under a reused key return 409,
and unsupported unsaved contexts return upgrade/validation errors. Submitted
analysis/project snapshots never override owned database context. There is no
direct-provider fallback under the enabled flag.

Pending POSTs return `{operationId, status, statusUrl, deadlineAt}` with 202,
Location, Retry-After and the echoed command key. The operation-resource ID is
different from the command key. Completed redelivery returns the saved original
success envelope or terminal failure. `GET /api/v2/llm-operations/{id}` is
owner-filtered and read-only; it cannot claim, renew or recover work.

The frontend saves immutable keyed commands in owner-scoped session storage
before POST, handles 202 before parsing a result, and polls every two seconds.
Reload, lost responses and authentication failures retain the same command.
New commands intentionally use new keys. Current edit/revision guards prevent a
late result replacing new requests/manual text. Manual material replacement
still requires confirmation; cancellation/failure preserves the text.

Below client materials, the localized dropdown uses the detected request language
unless explicitly overridden. New request text resets the old override, and
saved results restore their own selection. Translation changes text/labels only,
retaining verdict, amounts, currency, scope and timeline values.

## Language and domain calibration

Lingua runs offline over the existing supported-language set. Initial tunable
values are confidence 0.80, runner-up margin 0.20, dominance 0.75 and at least
12 alphabetic characters. They are policy values, not accuracy guarantees.
Foreign spans only count as strong mixed-language evidence when they independently
meet the same confidence/margin/length checks; shared Russian/Bulgarian vocabulary
is covered by a regression. URLs, verified names and verbatim frozen citations
are excluded from generated-prose evidence. Short labels use grouped evidence.

Coverage includes RU/ES, EN/RU, RU/EN, Spanish punctuation and accented prose,
short `Hola`, SEO, URLs, emoji and substantial mixed-language prose. Uncertain
input uses the visible interface-language fallback or explicit override. An
uncertain/wrong-language generated field triggers correction and then failure,
rather than successful publication with a language tag alone.

Typed/domain checks cover scope-position equality, verbatim citations, hourly
math, invented numerical commitments and representative free/included/timeline
contradictions. Translation checks localized amount/unit/currency Decimal
bindings and occurrence counts, including Spanish hours/euros/USD cases. These
checks reduce risk; they cannot detect every commercially meaningful contradiction,
spelled-out quantity, new unit or idiomatic promise. Wider language calibration
and bounded real-model evaluation remain necessary.

## Verification evidence

Tests use real pinned SDKs with injected HTTP responses and owned disposable
PostgreSQL 17. They are not real-model acceptance tests. The focused native bridge
was an early implementation gate. PostgreSQL scenarios cover idempotency,
ownership, concurrent admission/reservations, stale epochs, late edits,
once-only publication, unknown usage/cost, per-call bound violations, accepted
stage recovery after publication rollback and restart during provider dispatch.
The latter records the first uncertain call and resumes the same semantic request
with its remaining transport attempt, without an HTTP request or GET trigger.

The acceptance pipeline covers language matrix, repeated historical regeneration
after scope changes, one wrong-language correction, exhausted corrections,
explicit translation/override and History restoration, new-request reset,
confirmation/failure preservation, current-rate estimate refresh and unchanged
History check count. Frontend regressions cover stable retry keys through reload
and auth failures and server-owned language metadata through concurrent autosave.

Final verification on the implementation tree:

| Check | Outcome |
| --- | --- |
| Backend full suite, `pytest tests --require-integration` from `backend/` | 506 passed in 297.99 s; owned disposable PostgreSQL and test containers |
| Frontend Vitest, bounded to two workers | 47 files, 333 tests passed in 47.16 s |
| Ruff lint / formatting | Passed; 307 files formatted |
| Mypy, normal and Windows platform | Both passed; 197 source files |
| Frontend generated API types / TypeScript | Passed |
| Frontend ESLint | Passed with one existing unused-variable warning in `lib/llm/schema.test.ts` |
| Next.js production build | Passed; compiled in 3.4 s; separate TypeScript check passed |
| Exported OpenAPI freshness | Passed; regenerated only for changed operation/status/restore contracts |
| Compatibility / gateway harness | Passed controlled frontend/contract/auth/generation/Draft and entrypoint checks |
| PDF fixture / visual check | Passed; all 14 generated pages inspected |
| LLM Compose render | Passed with synthetic configuration; no application stack activation |

The earlier author's 26-test claim and approximately 1.993 ms, zero-call local
normalization reproduction are historical planning evidence. Its incomplete
asynchronous subset is not a passed suite. A current 8-test baseline rerun passed
in 0.10 seconds. An incorrectly launched final run from the repository root was
interrupted because migration tooling requires the backend working directory;
the corrected run uses that directory. Windows temp/process permissions required
owned repository-local test directories and authorized child-process access.

The compatibility harness passed frontend, contracts, auth, generation and Draft
journeys, plus existing Docker entrypoint checks, with controlled providers and
disposable PostgreSQL. The existing PDF fixture check passed and all 14 pages
were visually inspected: EN/RU/ES/DE, long text, missing fields and oversized
values. The LLM Compose overlay rendered successfully with synthetic configuration;
no application stack was started or migrated.

A fresh-context, read-only final review found no Critical findings. All five
Important findings were fixed with regressions: amount/unit swaps, auth retry-key
retention, trusted History override restoration, a reported cost above its call
reservation and historical estimate refresh using stale commercial values.

## Measurements and live limitation

Controlled nominal new checks make three outbound provider requests; a single
semantic correction adds one. An interrupted dispatch followed by resumption
uses four recorded attempts for a three-stage check, including the uncertain
first outcome. Actual-wire tests count corrections and transport retries;
rejected responses remain in cost accounting. The previous monolithic generation
path structurally used one nominal request, while the historical normalization
reproduction itself made zero. These are call-count comparisons, not a matched
real-provider performance benchmark.

Zero live calls were made. A key is configured, but `gpt-5.6-luna` has neither a
usable local tariff nor configured operator bounds; admission therefore refuses
the call. Real-model latency, token usage, baseline/new cost and invoice savings
are unavailable. Synthetic test tariffs and run durations must not be presented
as measured provider spend/latency. A later bounded smoke test requires a valid
bound and uses the predefined shared maximum of 24 physical calls, including
corrections and transport retries, without logging the key.

## Operator rollout and remaining risks

1. Stop writes and follow the existing ANY-549 maintenance/backfill procedure if
   not already at its approved baseline. Apply and verify `0005_llm_workflow`
   using the guarded migration runner before enabling the new application path.
   Do not use development/verification to migrate an application database.
2. Deploy matching API/frontend/worker images. Enable `SCOPE_GUARD_WORKFLOW_V2`
   and `SCOPE_GUARD_LLM_WORKFLOW` on API/LLM worker and the existing frontend
   workflow flag. Set migration target `0005_llm_workflow`. The existing API
   container entrypoint remains the guarded migration owner; its post-rollout
   rerun is idempotent. API lifespan and LLM worker schema checks are read-only.
3. Set `SCOPE_GUARD_WORKER_ROLE=llm`, shared database/key/model, conservative
   `SCOPE_GUARD_LLM_INPUT_RATE_BOUND` and `SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND`
   (USD/token), and `SCOPE_GUARD_LLM_MAX_COST` if changing the default. The existing
   environment model/alias behavior is preserved. Use `compose.llm.yaml` with
   `compose.workflow.yaml`; the worker reuses the export-worker build target and
   has a 40-second shutdown grace. Confirm readiness before allowing admission.
4. Upgrade external legacy callers to saved Draft references, revisions, stable
   command keys and 202/polling. Roll back matching application images/flags
   without removing call accounting or reversing maintenance migrations.

Production LLM-worker process-level kill/SIGTERM drills and real-provider
calibration were not performed. Stage cancellation/restart and general container
signal behavior are covered separately by controlled tests. UI polling can
continue briefly after unmount, but is bounded by the operation deadline and
does not execute work. The existing process-local admission limiter still
requires one production API worker/replica. Detector/domain rules are finite and
need future calibration. An external call after timeout can have executed and
been charged despite no response. Related product tickets are not declared
complete merely because these integrations are present.
