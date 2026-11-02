# ANY-803: PydanticAI delivery; LiteLLM upgrade blocked

Date: 2026-11-02. ANY-803 remains incomplete. No Linear statuses/comments changed.

## Delivered scope and base

Base: dab092029043d08ce93d224cd83080f2de825800 (fetched origin/main).
Branch: codex/any-803-llm-dependency-security, retained authorized ANY-801 worktree.
Implementation commit: 6793788dd1f2b8537101eb04ad06a1c77b731acf.
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
Adapter, gateway, worker, prompts, workflow and DB schemas unchanged. policy.py now derives
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

Fresh candidate checks image from official Dockerfile, locked install; no host candidate sync.
Tests used only synthetic keys and HTTP providers, no real env/home/SSH/cloud mounts or Docker socket.
Host orchestrator created disposable PostgreSQL on internal scg-any803-isolated network;
provider/public egress unavailable. Config/fixture mounts were read-only. No paid calls.
Candidate matrix used installed image packages, not primary source overlay.
Baseline schema comparison used old SDK image plus sanitized read-only application source snapshot.

Focused candidate command: tests/unit/test_gateway_responses_bridge.py,
tests/unit/test_optional_diagnostic_review.py, tests/integration/test_llm_pipeline.py,
tests/integration/test_optional_review_sql.py, plus tests/unit/test_llm_tariff_provenance.py:
**44 passed**. Same four baseline files on old SDKs: **42 passed**.

| Behavior | Baseline and candidate |
|---|---|
| Timeout | 2 gateway-owned transport attempts |
| Wrong language then 429 | 3 physical requests; (1,1), (2,1), (2,2) |
| Provider schema rejection | 1 physical request; no fallback/downgrade |
| Exhausted output corrections | 3 bounded semantic attempts |
| Native schema | strict; required fields; additionalProperties=false |
| Correction context | prior rejected output and validator feedback preserved |
| Usage | absent usage remains unknown; IDs/token/cost interpretation retained |
| Review false | no diagnostic provider dispatch |
| Review true / replay | bounded dispatch; accepted replay does not redispatch |
| PostgreSQL | budgets, actual-cost overruns, fencing, restart, publication isolation pass |

Prepared schema digest sets identical across baseline/candidate for all six schema-name groups
exercised (including four semantic-review variants). This proves fixture compatibility, not all
possible historical operations. Existing prepared-schema equality guard remains unchanged;
incompatible unfinished requests fail workflowVersionUnavailable instead of being silently replayed.

New tariff test reproduced failure before the fix; both tests pass with the fix. Frozen policy
SQL/restart behavior is covered separately by integration tests, not inferred from dictionary copies.
Ruff check/format passed all 433 backend/API files. Linux and win32 mypy each passed 248 source files.
OpenAPI export freshness, frontend api-types check, and 14 synthetic CI configuration tests passed.
Independent code review found no actionable defects. Full CI and broad-suite results are recorded below
when observed; pending checks are not passes.

Docker Desktop initially failed with WSL bootstrap error/unexpected EOF; user restored it.
The initial checks image SQL attempt lacked read-only migrations (24 setup failures); corrected
harness rerun is the 44-pass result above. No SDK/business expectations were weakened.

## Fresh runtime images

Both images built from final lock and implementation commit; inspected installed versions match
the table above. No runtime source overlay. Revision labels below refer to implementation code;
later documentation-only commits do not change runtime sources.

- scg-any803-api:verification: `sha256:516fb77538ec3db0f556477208f2b571877112578b2f2278117e181a8235f718`; revision `6793788dd1f2b8537101eb04ad06a1c77b731acf`.

- scg-any803-worker:verification: `sha256:8243bcf5c70a5fa043b22481afc7e8bd1ec61c531b4bbb63f45f7ad0a001cfd1`; revision `6793788dd1f2b8537101eb04ad06a1c77b731acf`.


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
