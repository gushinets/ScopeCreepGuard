# ANY-803: PydanticAI delivery; LiteLLM upgrade blocked

Date: 2026-11-02. ANY-803 remains incomplete. No Linear statuses/comments changed.

## Delivered scope and base

Base: dab092029043d08ce93d224cd83080f2de825800 (fetched origin/main).
Branch: codex/any-803-llm-dependency-security, retained authorized ANY-801 worktree.
Final implementation commit: f1c8dfc28bcdf3be3df39bc3e4827d8f6d1cada0.
Initial dependency/policy checkpoint: 6793788dd1f2b8537101eb04ad06a1c77b731acf.
Primary checkout, its branch, untracked reports, private environments and unrelated services preserved.
Plan: plans/2026-11-02-any-803-llm-dependency-security.md.

| Dependency | Before | After |
|---|---|---|
| pydantic-ai-slim | 2.2.0 | 2.64.0 |
| pydantic-graph | 2.2.0 | 2.64.0 |
| genai-prices | 0.1.11 | 0.2.1 |
| litellm | 1.89.3 | retained |
| filelock | 4.2.1 | retained |
| httpx2 / griffelib | 2.13.1 / 2.3.2 | retained |

These are all package-version changes. Minimal Slim installation and no extras retained.
uv 0.11.19 generated the lock; its revision field normalized 5 -> 3. No edited package metadata/hashes.
The native bridge adapts the new SDK retry-feedback boundary (details below). Gateway, worker,
prompts, business workflow and DB schemas remain unchanged. policy.py now derives
local-tariff priceSource from installed LiteLLM distribution metadata. Operator rate precedence
and per-operation frozen policy remain intact; stored operations are not repriced.

## Security gate and audit

LiteLLM latest official stable remains 1.106.6, requiring filelock>=3.16.1,<4.0.
No corrected stable release was available. Latest satisfying filelock is 3.32.7, with 13
OSV GHSA findings; GHSA-69hj-f68j-2879 affects all <4 and is fixed in 4.2.1.
User explicitly chose to retain LiteLLM and secure filelock, independently updating PydanticAI.
LiteLLM 1.106.6 was not installed/executed. Malicious 1.82.7, 1.82.8, 1.107.0 excluded.

Fresh OSV querybatch covered all 101 registry packages including dev dependencies.
Only retained LiteLLM matched GHSA-3cv6-jpf6-8222 and GHSA-g5ff-637f-6q2m, plus PYSEC alias.
They concern authenticated LiteLLM proxy routing and its Vertex credentials transform endpoint.
This application uses a custom SDK Responses bridge with operator-controlled provider arguments,
no LiteLLM proxy endpoint/extras. Findings remain reported, not suppressed or called fixed.
No advisory match for the updated PydanticAI/Graph/genai-prices graph at audit time.
OSV absence is not proof of benign code or a complete supply-chain audit.

| Wheel | SHA-256 | Provenance result |
|---|---|---|
| pydantic_ai_slim-2.64.0 | 63ccfe3f66beefb0a2fb3843d471f9d5b74a432f4436ed5ceb7e0d6bb06cb1e4 | cryptographically verified |
| pydantic_graph-2.64.0 | 5034949fd78899001b31b819e3fd9357019766d48245f788712bb3a91ccf75a2 | cryptographically verified |
| genai_prices-0.2.1 | b438753161537f2e2a5c937887721467dd5a24297a52ae77f946f541ce22c3a0 | PyPI 404 |
| httpx2-2.13.1 | 6dff50fabc270ee5fd25d845d0b078ed20564579744d6d962850975996d2f9a4 | PyPI 404 |
| griffelib-2.3.2 | 8e710afededd5607f95bf3c8ccc175ee306e7084459faf27b9f9f44ef2a7a274 | PyPI 404 |

pypi-attestations 0.0.30 verified both exact Pydantic wheel files with repository constraint
https://github.com/pydantic/pydantic-ai in a separate disposable trusted-tool container.
This is cryptographic verification, not merely decoded publisher metadata, and does not prove code benignness.
All five wheel hashes match PyPI, RECORD hashes verified, no unsafe paths/startup hooks/native libraries.
All 12 genai-prices Python files matched official v0.2.1 source. Static review inspected transport
and source-loader/subprocess surfaces in retained httpx2/griffelib. Their missing attestations
remain explicit limitations; no real credentials were exposed during evaluation.
For blocked LiteLLM, Linux wheel ec3cae6c87971657c9ae905b6d23aef456e979c8848f22bbc5096a31e1a1da4d
has 2776 matching Python source files but an independently unverified native library and no
PyPI provenance (404). The earlier ac74f9ff... hash belongs to macOS x86_64, not Linux.

## Compatibility evidence and containment

No candidate sync into host/primary environments. Only synthetic keys and HTTP providers;
no real env/home/SSH/cloud mounts or Docker socket in candidate test containers.
Host orchestrator owns disposable PostgreSQL on internal scg-any803-isolated network,
with provider/public egress unavailable. No paid calls. Source snapshots contain tracked
public implementation/test files only, excluding private env/WORKLOG files.

Initial baseline comparison used tests/unit/test_gateway_responses_bridge.py,
tests/unit/test_optional_diagnostic_review.py, tests/integration/test_llm_pipeline.py and
tests/integration/test_optional_review_sql.py: old SDKs 42 passed, candidate plus tariff tests
44 passed. Prepared-schema digest sets matched across six schema groups, including four
semantic-review variants. Baseline used old SDK image plus read-only source overlay; initial
candidate checks used fresh baked-image application code and current SDKs.
This narrow matrix was insufficient to establish durable rejection-feedback compatibility.

Expanded tests and first CI found the compatibility gap: PydanticAI 2.64 public
Model.prepare_messages translates RetryFeedbackPart to safely fenced UserPromptPart before
request(), bypassing the bridge's legacy RetryPromptPart-only ledger hook. Output correction
still happened, but durable rejected-call feedback was lost. Initial CI c9b38f0 had 28 failures,
including seven SQL translation scenarios; its other four CI jobs passed. No tests were weakened.

Minimal fix in GatewayResponsesModel: capture typed feedback after the latest ModelResponse
before delegating to super().prepare_messages; drain it to the existing gateway feedback hook
before the next dispatch. SDK attribution/fences and previous rejected output remain intact.
No private SDK APIs used; no retry ownership, strict schema, tool mode, budgets or pricing changes.
Earlier feedback is not replayed onto a later rejection. Existing final-attempt handling remains.

RED: strengthened real HTTP bridge assertions failed for medium/high effort on missing durable
feedback. GREEN: 140 gateway/translation/regeneration/reply-similarity regressions passed.
Expanded unit/architecture: 841 passed, one Node auth interop test deselected locally because
Windows pnpm links cannot be loaded by Linux Node. That test remains enabled in full CI.
Tests used a copied disposable-container filesystem after Windows bind reads intermittently
returned EINVAL; no product change was made to address test filesystem errors. Storage test
writes were confined to the disposable filesystem. Independent review found no actionable defects.

| Contract | Preserved result exercised by tests |
|---|---|
| Timeout | 2 gateway-owned transport attempts |
| Wrong language then 429 | 3 physical requests; (1,1), (2,1), (2,2) |
| Provider schema rejection | 1 physical request; no fallback/downgrade |
| Exhausted output corrections | 3 bounded semantic attempts |
| Native schema | strict; required fields; additionalProperties=false |
| Correction context | rejected assistant output, feedback and SDK retry fence |
| Durable feedback | rejection recorded against prior physical call, not transport retry |
| Usage | missing remains unknown; IDs/token/cost interpretation retained |
| Review false | no diagnostic provider dispatch |
| Review true / replay | bounded dispatch; accepted replay does not redispatch |
| PostgreSQL initial matrix | budgets, actual-cost overruns, fencing, restart, publication isolation |

Tariff test reproduced the hard-coded-label defect before the fix, then passed; frozen SQL
policy/restart evidence is separate from the dictionary-copy unit assertion. Ruff check/format
passed 433 files. Both mypy targets passed 248 source files before the feedback adaptation;
Linux mypy also passed after it. OpenAPI, frontend API types and 14 synthetic CI config tests passed.
Post-adaptation local Windows mypy and final 51-test SQL matrix were interrupted by Docker WSL
failure, not reported as passing. Final matrix printed installed versions and bridge path
/app/.venv/lib/python3.12/site-packages/scope_guard/integrations/llm/pydanticai_model.py,
confirming no source overlay, before the interruption.

Complete backend suite, both current mypy targets, contracts/PDF checks, frontend, full Compose
smoke and recovery journeys run in [PR #62 checks](https://github.com/gushinets/ScopeCreepGuard/pull/62/checks)
on the proposed merged state. Consult that check record for current full-CI outcomes; do not
substitute the initial 44-test pass for full verification. No disabled or weakened checks.

## Fresh runtime images and local infrastructure limits

Final API/worker builds completed from f1c8dfc and the final frozen lock. A disposable copy of
the official apps/api/Dockerfile changed only build-time uv concurrency to one for installs,
downloads and builds after repeated Docker Desktop interruptions. Repository Dockerfile and
runtime settings are unchanged. Full CI uses the unchanged official Dockerfile.

Successful local BuildKit export records (manifest-list digests, not post-build inspect results):

- scg-any803-api:final: sha256:9d4ba3fd9c06cf1f546328a3c542e94a73ab786e93cf5d295d1e29eaedde56a6.
- scg-any803-worker:final: sha256:cae2a5e3c7dd56bb55133ce6ef08ac06c6f031957a53cc3d2f5af83b54b22e49.
- Config digests: API 87e0317eecd0e752879c3d9bfbe29b6d7f0ee3b9d5d2c6a6f845f25ff089f921;
  worker 6204f23ec35ef6ff72d804dc019b2f3797b9abcfeaa5377b9a49f21226246eca.
- Configured SOURCE_REVISION label: f1c8dfc28bcdf3be3df39bc3e4827d8f6d1cada0.

Final post-build Docker inspect failed because Desktop/WSL became unavailable again; configured
labels above are not represented as independently inspected metadata. Earlier images at 6793788
were inspected successfully, but they predate the required bridge fix and are not final acceptance.
Final checks image installed-version metadata confirmed LiteLLM 1.89.3, filelock 4.2.1 and
Slim/Graph 2.64.0. Remaining final runtime verification is covered by official-image CI checks.

Docker Desktop repeatedly failed with WSL bootstrap 0xc00000fd / unexpected EOF; root cause is
not established and not attributed to the SDK. The user restored Docker once. No engine restarts,
volume removals, production DB resets or unrelated-service changes were performed by this task.
Owned resources, if retained after recovery: scg-any803-isolated network; any803-pg with label
scope-guard.disposable=any803-pydantic, most recent ID
7bc50e8e333329c3571cab1f03ab0cc27185e61f2574945628eed9653b717d24.
Inspect identity/labels before cleanup; do not remove any volume. Final temporary test container
has label scope-guard.disposable=any803-final; host orchestrator owns cleanup.

## Deployment, unfinished operations and rollback

No DB migration introduced. Follow existing documented maintenance update and one-shot migration gate.
Before deployment stop new enqueue and drain both user and diagnostic lanes with old images; confirm
no unfinished operations, active leases or unknown provider outcomes. Do not delete or reinterpret them.
If draining cannot complete, defer upgrade or retain the compatible old workers for operator resolution.
This conservative drain remains recommended despite matching fixture schemas. API/workers do not
mutate schema at startup. ANY-764 stays disabled by default; findings remain internal, not acceptance gates.

Deploy application code + manifest + lock + freshly built API/worker images together. Rollback restores
all four from the previous compatible revision; package-only rollback is not sufficient for policy code.
Existing operation prices remain frozen. Never reset existing DBs, remove existing volumes or restart
unrelated services. Full readiness requires all documented services/private storage/Mailpit; bounded
local SDK/SQL/image checks alone do not establish full application E2E.

## Delivery and remaining scope

One Pydantic-only PR targets main. Do not close ANY-803: LiteLLM upgrade remains blocked upstream.
Dependabot #58 (LiteLLM 1.100.4) and #59 (Slim 2.53.0) were already closed without merge, unchanged
by this task. This delivery supersedes #59's older Slim proposal; #58 is not implemented by it.
No merge, force-push, PR retarget/closure, or Linear write performed.

Sanitized detailed evidence: primary output/any803-pydantic and output/any803-security-gate.
Sources: https://pypi.org/pypi/litellm/1.106.6/json ; https://pypi.org/pypi/pydantic-ai-slim/2.64.0/json ;
https://github.com/tox-dev/filelock/security/advisories/GHSA-69hj-f68j-2879 ;
https://github.com/BerriAI/litellm/security/advisories/GHSA-3cv6-jpf6-8222 ;
https://github.com/BerriAI/litellm/security/advisories/GHSA-g5ff-637f-6q2m .
