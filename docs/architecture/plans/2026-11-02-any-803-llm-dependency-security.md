# ANY-803: LLM dependency security implementation plan

Date: 2026-11-02. Current status: PydanticAI implementation verified locally; LiteLLM upgrade remains blocked.

Current evidence and deployment record: [PydanticAI delivery report](../2026-11-02-any-803-pydantic-security.md).
Final implementation: f1c8dfc28bcdf3be3df39bc3e4827d8f6d1cada0.
Initial 44/42 matrix found matching schemas; broader tests exposed typed retry-feedback
accounting incompatibility. The public prepare_messages adaptation fixes it; 140 targeted
and 841 unit/architecture tests passed after the fix. One local Node interop test stays
covered by unchanged full CI. Final local SQL/mypy attempts were interrupted by recurring
Docker Desktop failures. See PR #62 Checks for final full-suite/image/merged-state evidence.
No failing check was weakened. Runtime builds completed; final local inspect unavailable.
Earlier checkpoints below are historical, not current gate results. ANY-803 remains
incomplete; LiteLLM stays blocked and must not be downgraded around secure filelock.

## Original plan and historical checkpoints

Goal: update LiteLLM and minimal PydanticAI Slim together without changing transport,
accounting, strict output, user workflow or optional internal diagnostics.
Architecture: retain ProviderGateway as sole retry/ledger owner and GatewayResponsesModel
as the NativeOutput bridge. Change only dependency pins and proven API incompatibilities.
Tech stack: Python 3.12, uv, LiteLLM Responses, PydanticAI, PostgreSQL, Docker Compose.
Spec: user ANY-803 request and local preliminary report
`docs/architecture/2026-11-02-any-803-dependency-preresearch.md` in the primary checkout.
Execution: inline, after presentation; no extra worktree or clone, no extra approval
except a material unresolved security/compatibility decision.

## Base, branch and preservation

- Actual fetched origin/main/base: dab092029043d08ce93d224cd83080f2de825800.
- Working branch: codex/any-803-llm-dependency-security.
- Authorized reused checkout: D:/.codex/worktrees/any-801-vite-security/ScopeCreepGuard.
- Before reuse: clean tracked/untracked status; previous ANY-801 chat idle with a final
  response. PR #61 merged at dab0920. Previous branch retained; no history rewritten.
- Primary checkout remains ff64a458ba7871e627b290284c9061cf35bc8aab on
  codex/any-769-pdf-preview-draft-id. Three untracked reports and ignored evidence preserved.
- Dependabot #58 (LiteLLM 1.100.4) and #59 (Slim 2.53.0) already closed, unmerged.
  They are stale separate proposals, not compatibility evidence. No PR actions taken.
- No private env files, credentials, environments or service state copied.

## Selection and security gate

- Current PyPI stable versions rechecked: LiteLLM 1.106.6, Slim/Graph 2.64.0.
  These remain evaluation candidates, NOT an approved final production selection.
- Exclude LiteLLM 1.82.7, 1.82.8 and 1.107.0, confirmed by current official incident reports.
- Baseline LiteLLM/Slim/Graph: 1.89.3 / 2.2.0 / 2.2.0.
- Proposed direct pins: litellm==1.106.6, pydantic-ai-slim==2.64.0;
  Graph must resolve to its declared ==2.64.0. No provider/proxy/MCP/UI/tool extras.
- LiteLLM candidate requires filelock>=3.16.1,<4.0 and huggingface-hub>=0.34.0,<2.0.
  Current graph owns filelock through huggingface-hub 2.2.0. Thus both a filelock
  downgrade and a huggingface-hub change need explicit evaluation, not just the two SDK pins.
- Latest non-yanked stable filelock below 4 is 3.32.7. Fresh exact OSV query returns
  13 GHSA records. GHSA-69hj-f68j-2879 affects every version <=4.2.0 and is fixed in
  4.2.1. There is no advisory-free version satisfying the new LiteLLM constraint.
- Current filelock 4.2.1 must not be silently downgraded or forced past upstream metadata.
  Final candidate selection is blocked pending a compatible corrected upstream release
  or an explicit, evidence-based security exception. Do not arbitrarily pick another SDK.
- Advisory applicability is conditional on local filesystem attackers/access. Production
  lock/cache ownership and permissions have not been demonstrated; isolation of tests
  does not demonstrate production mitigation. No exploit or production inspection authorized.
- LiteLLM preliminary wheel hash ac74f9ff9faae1a424dc7be873b80ccf1cea1681a9f4dac03bac068ae3a8d8b0
  is the macOS x86_64 wheel, NOT the deployment Linux wheel. Linux manylinux x86_64:
  ec3cae6c87971657c9ae905b6d23aef456e979c8848f22bbc5096a31e1a1da4d.
- Broaden comparison to all Python files against pinned source commit
  61c6ab78393ef45683dd7d963d2a315bd845e20b; inspect native members separately.
  Source comparison, RECORD and PyPI hashes are not cryptographic publisher verification.
- Slim wheel: 63ccfe3f66beefb0a2fb3843d471f9d5b74a432f4436ed5ceb7e0d6bb06cb1e4.
  Graph wheel: 5034949fd78899001b31b819e3fd9357019766d48245f788712bb3a91ccf75a2.
  Published provenance exists; cryptographic verification is outstanding. Use established
  pypi-attestations/Sigstore tooling in a separate trusted environment, checking repository,
  workflow, subject digest and transparency proof. Decoding metadata is insufficient.
- httpx2 and griffelib are mandatory for Slim 2.64.0, but already appear in the baseline
  lockfile (2.13.1 / 2.3.2). Preserve if compatible; inspect exact artifacts and transitives.
  Do not float them to current latest (2.16.0 / 2.4.1) without need.

## Ordered execution and checkpoints

- [x] Read preliminary report, workspace state, completed chat, issue, PRs and current metadata.
- [x] Fetch main and create ordinary branch in the sole authorized clean worktree.
- [ ] Resolve material filelock security decision before implementation.
- [ ] Finish platform-specific artifact/source comparison and cryptographic verification
  where available; record native binary and missing-provenance limitations explicitly.
- [ ] Resolve full workspace graph with uv lock --no-build after updating ONLY LiteLLM pin.
  Record every package/version/hash delta including mandatory minimum bumps. Do not sync host env.
  Audit entire graph including dev groups with trusted tooling; do not suppress findings.
- [ ] In disposable Docker test environment install wheels from frozen lock, synthetic keys,
  no real env, no home/cloud/SSH mounts, no socket, no primary source, network none.
  Host orchestrates temporary PostgreSQL on an internal network when needed.
- [ ] Run transport/accounting comparison below; commit coherent LiteLLM checkpoint if passing.
- [ ] Update Slim pin, regenerate lock through uv, keep Graph exact; repeat static artifact
  and full graph audit before candidate execution. Run same comparison for combined graph.
- [ ] Fix policy.py priceSource using importlib.metadata.version('litellm') for local tariff.
  Preserve operator bound precedence and frozen prices on existing operations. Add focused
  test of installed-version label, operator label and unchanged persisted policy.
- [ ] Adapt litellm_adapter.py / pydanticai_model.py only for demonstrated API gaps.
  No planned gateway/worker/schema redesign or migration; new gaps require focused tests.
- [ ] Run full ci/scripts/check-backend.sh equivalents: pytest --require-integration, ruff
  check/format, Linux and win32 mypy, contract freshness, PDF verification; full repository CI.
- [ ] Build fresh API/llm-worker images from final lock with locked install. Record revision,
  local diff, image IDs and revision labels. Existing image/source-overlay results stay distinct.
- [ ] Review diff/evidence, commit and push scoped files only; create ONE main-targeting PR,
  verify actual head/base and current CI. No merge, Linear changes or Dependabot edits.

## Baseline comparison matrix

Reuse tests/unit/test_gateway_responses_bridge.py, tests/unit/test_optional_diagnostic_review.py,
tests/integration/test_llm_pipeline.py and tests/integration/test_optional_review_sql.py.
Preliminary baseline: 18 unit + 24 PostgreSQL tests = 42 passed; candidates NOT tested.

| Contract | Baseline / required result | Candidate result |
|---|---|---|
| Timeout | 2 gateway transport attempts, uncertain outcomes accounted | Pending |
| Wrong language then 429 | 3 physical calls; (1,1), (2,1), (2,2) | Pending |
| Provider schema rejection | 1 request, no downgrade/retry | Pending |
| Exhausted corrections | 3 bounded semantic attempts | Pending |
| Native schema | strict; required; additionalProperties=false | Pending |
| Correction context | prior rejected output and validator feedback transmitted | Pending |
| Usage | missing remains unknown; cached/reasoning and IDs preserved | Pending |
| Review off | no review dispatch, disabled by default | Pending |
| Review on / accepted replay | bounded review; replay no redispatch | Pending |
| SQL | reservations, actual overruns, fencing, cancellation, restart | Pending |
| Product | analysis, replies, regeneration, translation, estimate, agreement | Pending |
| Isolation | user edits, commercial facts, Draft/History; review internal | Pending |

No paid providers. Synthetic controlled HTTP responses only. Every physical dispatch
must have a durable provider-call row, with requested/actual model and response/request IDs.

## Unfinished operations, deployment and rollback

Compare baseline/candidate prepared schema dictionaries and serialized messages for each
stage and both review modes. Exercise stored prepared requests across restart, received
responses, unknown outcomes and accepted replay. Existing bridge rejects mismatched schema
with workflowVersionUnavailable; preserve this rather than silently replaying changed schemas.
Until cross-version equality is proven, maintenance requires blocking new enqueue, letting
existing user AND diagnostic lanes finish with OLD images, and checking no active leases,
pending provider outcomes or incomplete operations remain. Do not delete pending rows.
If draining cannot finish, retain old compatible workers or defer upgrade for operator resolution.

Follow documented maintenance entry points and one-shot migration gate. Use unique disposable
Compose names and synthetic fixtures for tests, private object storage and Mailpit; full E2E
requires all documented services. Workers never mutate schemas. No existing volumes removed,
databases reset, global volume names introduced or unrelated services stopped.
Rollback restores manifest + lock + adapter/policy code + matching old images together.
Do not recalculate stored tariffs or require a DB migration without a demonstrated need.

## Evidence and handoff

Owner: ANY-803 implementer; material risk acceptance belongs to repository/security owner.
Current blocker: no secure filelock range intersects LiteLLM 1.106.6's declared constraint.
No candidate installed/imported, no behavioral verification, no fresh images, no implementation
commit or PR yet. Do not claim production approval or completion.
Sanitized static evidence: primary output/any803-security-gate/; previous evidence unchanged.
Linear get_agent_context endpoint returned tool-not-found; no notes or statuses were changed.

Sources:
- https://pypi.org/pypi/litellm/1.106.6/json
- https://pypi.org/pypi/filelock/json
- https://github.com/tox-dev/filelock/security/advisories/GHSA-69hj-f68j-2879
- https://github.com/tox-dev/filelock/security/advisories/GHSA-8mx5-7m5m-r77g
- https://docs.litellm.ai/blog/security-update-march-2026
- https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain
- https://www.litellm.ai/security

## Static gate execution evidence (2026-11-02)

A metadata-only full workspace resolution completed with uv 0.11.19:
`uv lock --directory output/any803-security-gate/resolution --no-build --python 3.12`.
The scratch directory contains only copied public manifests/lock, not implementation,
credentials or environments. No sync, build, import or candidate execution took place.
The working manifests and lockfile remain unchanged. Resolution: 107 workspace packages,
104 registry packages including development dependencies. Fresh OSV querybatch found
only filelock 3.32.7, with 13 GHSA records. This is advisory matching, not a malware scan,
cryptographic verification or a complete security approval.

| Dependency | Before | Resolved evaluation graph |
|---|---|---|
| litellm | 1.89.3 | 1.106.6 |
| pydantic-ai-slim | 2.2.0 | 2.64.0 |
| pydantic-graph | 2.2.0 | 2.64.0 |
| filelock | 4.2.1 | 3.32.7 (REJECTED pending security decision) |
| huggingface-hub | 2.2.0 | 1.33.0 |
| genai-prices | 0.1.11 | 0.2.1 |
| boto3 | 1.43.112 | 1.43.123 |
| botocore | 1.43.112 | 1.43.123 |
| h2 | absent | 4.4.1 |
| hpack | absent | 4.2.0 |
| hyperframe | absent | 6.1.0 |

httpx2 2.13.1 and griffelib 2.3.2 were retained. All other package versions were
retained. This scratch resolution is evidence only, not the final incremental lock
update; evaluate minimal boto3/botocore changes when the gate can proceed.

Linux wheel broad comparison completed: 2776/2776 Python files byte-identical to the
pinned official source commit, no unmatched/changed Python files, no startup hooks.
Native member `litellm/rust_bridge/_native.abi3.so` exists and was NOT independently
reproduced or source-verified. Linux wheel provenance endpoint returned HTTP 404.
Do not extrapolate the Python comparison to the native binary or to cryptographic
publisher verification. Sanitized results: primary checkout
`output/any803-security-gate/litellm-linux-static.json`, `dependency-delta.json`,
`resolved-graph-osv.json`, and scratch `resolution/uv.lock`.

The filelock <4 upper bound is declared upstream wheel metadata; no maintainer
rationale or demonstrated 4.x compatibility was established. Neither changing
metadata nor ignoring its declared bound is authorized. Candidate behavioral tests,
image builds, cryptographic Pydantic verification, audit applicability acceptance
and production release approval remain outstanding. The previous 42 baseline tests
were not rerun or attributed to the candidate graph.


## Authorized split execution

User requested independent PydanticAI delivery, retaining current LiteLLM while no corrected
release supports filelock>=4.2.1. ANY-803 as a whole remains open. Latest official PyPI
LiteLLM is still 1.106.6 with filelock<4; do not install it. Current branch/base unchanged.

1. Resolve only Slim==2.64.0 / Graph==2.64.0: metadata-only resolution changes only these
   plus genai-prices 0.1.11 -> 0.2.1; LiteLLM 1.89.3 and filelock 4.2.1 retained.
2. Audit all runtime/dev registry packages; inspect mandatory httpx2/griffelib and new
   genai-prices artifacts, verify available Pydantic provenance cryptographically.
3. Update working manifest and generated lock only after static gate; execute tests in
   disposable containers with no provider egress or secrets. Host owns disposable DB.
4. Fix tariff provenance and only demonstrated bridge API gaps; run original comparison
   matrix, source/schema restart comparison, lint, both mypy platforms and contracts.
5. Build fresh API/worker images, document actual verification and remaining findings;
   one main-targeted PR clearly delivers PydanticAI only and leaves LiteLLM blocked.

Fresh graph OSV results include retained LiteLLM findings GHSA-3cv6-jpf6-8222 and
GHSA-g5ff-637f-6q2m (plus PYSEC alias). These are not suppressed or represented as fixed.
New/retained companion artifacts lack PyPI provenance (404); bounded static review and
no-secret/offline behavioral containment do not establish cryptographic publisher identity.


## Pydantic-only implementation checkpoint — runtime verification blocked

Working changes: Slim 2.2.0 -> 2.64.0, Graph 2.2.0 -> 2.64.0, genai-prices
0.1.11 -> 0.2.1. No other package versions changed; LiteLLM 1.89.3, filelock
4.2.1, httpx2 2.13.1, griffelib 2.3.2 retained. uv 0.11.19 generated the lock
(including revision 5 -> 3 normalization); no hand-edited hashes/metadata.
`uv lock --check --no-build --python 3.12`: 104 packages resolved, success.

Cryptographic verification: pypi-attestations 0.0.30 installed in a disposable
python:3.12-slim verifier container with no secrets, socket or home mounts.
`verify pypi --repository https://github.com/pydantic/pydantic-ai` succeeded for
both exact Slim/Graph wheel files. This checks signed provenance, not code benignness.
Their SHA-256 values are recorded above. Companion wheel SHA-256:

| Artifact | SHA-256 | PyPI provenance | RECORD verified |
|---|---|---|---|
| genai_prices-0.2.1 | b438753161537f2e2a5c937887721467dd5a24297a52ae77f946f541ce22c3a0 | 404 | 17 |
| httpx2-2.13.1 | 6dff50fabc270ee5fd25d845d0b078ed20564579744d6d962850975996d2f9a4 | 404 | 35 |
| griffelib-2.3.2 | 8e710afededd5607f95bf3c8ccc175ee306e7084459faf27b9f9f44ef2a7a274 | 404 | 49 |

No startup hooks, unsafe archive paths or native libraries in these five inspected
wheels. All 12 genai-prices Python files matched official v0.2.1 source. Static
httpx2/griffelib review identified documented HTTP transport / explicit Git and
source-loader subprocess capabilities, not a proof of absence of malicious code.
No new provider/tool extras enabled. genai-prices updater requires explicit start;
application authoritative costs continue to use frozen policy, not this updater.

Fresh full-graph OSV query: 101 registry packages (104 including workspace packages),
only retained LiteLLM matched: GHSA-3cv6-jpf6-8222, GHSA-g5ff-637f-6q2m and
PYSEC-2026-4066 alias. These affect authenticated LiteLLM proxy request routing /
Vertex credential loader via /utils/transform_request. This application uses SDK
Responses with operator-controlled arguments, no LiteLLM proxy endpoint or extras.
No claim of whole-package security or resolution of the blocked LiteLLM update.

Policy changes: derive local tariff priceSource from importlib.metadata.version;
operator bounds unchanged. Targeted test first reproduced the hard-coded label
(1 failed, 1 passed against prior implementation, network none). Fix is implemented
but GREEN runtime test is still outstanding. Tests also retain a saved policy value
when later installed-version attribution changes. No DB schema/adapter changes.

Fresh checks image built successfully from current manifest/lock using official
apps/api/Dockerfile checks target, locked installs. Build source: base dab0920 plus
manifest/lock/policy changes; label argument dab0920-any803-pydantic-local (checks
stage has no runtime revision label). Build output config digest:
sha256:d516304977bb5ee4d6b4325dbbe6cbc43cc76279fcc208e32cead7634ac64af1.
Manifest list: sha256:8d4599a1aa356e2c45a1ab9274d29cc2b998fdfcec7ee96dbbb5a98bc98520d4.
Docker inspect confirmation is unavailable after engine failure; do not present
these as inspected release-image IDs. Final runtime API/worker images remain unbuilt.
One subsequent policy quote-format change requires final rebuild even though behavior
is unchanged. No candidate packages installed into the host or primary environment.

Verification attempted:
- Candidate 42 baseline regressions + 2 tariff tests on installed fresh-image packages,
  read-only tests/config only. Internal network to owned PostgreSQL, synthetic key.
- Baseline schema comparison on prior SDK image with source overlay, same fixtures.
- Linux and win32 mypy plus lint in network-none container.
All three container commands were interrupted by Docker engine failure / unexpected EOF;
none is a passing run, and schema comparison has no completed result.
- Host existing ruff 0.16.10 (no candidate installation): check and format check passed
  across 433 backend/API files. git diff --check passed.
- Contract freshness, full pytest/CI, final images, restart cross-version matrix pending.

Infrastructure blocker: Docker reports Desktop/Wsl/ExecError, bootstrap exit
0xc00000fd, unable to start engine. Root cause is not established; do not attribute
it to SDK behavior. No engine restart, volume removal, database reset or unrelated
service changes performed. User input requested because restarting the shared engine
may affect other services. Owned resources, if retained after engine recovery:
network scg-any803-isolated; PostgreSQL any803-pg (label
scope-guard.disposable=any803-pydantic, original ID
4c45ca7539d16c02f4d8ea7b27c363c22fa1ac58d2b87cb5f1dd345861a518a8).
Host owns lifecycle; no Docker socket exposed to candidate code. On recovery inspect
identity/ownership before any cleanup. Do not remove any volume.

Next: restore Docker with user authorization, rerun verification sequentially, compare
schema digests, address demonstrated gaps, build final API/worker images and complete
CI. Only after successful verification commit/push and create the scoped Pydantic-only
PR. No implementation commit/push/PR yet. ANY-803 remains incomplete; LiteLLM stays
explicitly blocked. Previous reports, branches, primary checkout and services preserved.

Sanitized evidence remains in primary output/any803-pydantic/: audit.json, artifacts.json,
record-and-source.json, provenance-verification.log, build-checks.log, focused.log,
baseline-schemas.log and static-checks.log. No private prompts, credentials or data.
