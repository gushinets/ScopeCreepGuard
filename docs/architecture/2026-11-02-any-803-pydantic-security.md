# ANY-803: combined LiteLLM and PydanticAI security update

Date: 2026-11-02. Implementation ready for review, subject to current PR checks.
No merge or Linear status/comment changes. This final record supersedes the preliminary
1.103.10 investigation and earlier Pydantic-only blocker statements; those checkpoints
remain historical evidence, not the final runtime/security verdict.

## Revision and dependency changes

Existing branch/check-out: codex/any-803-llm-dependency-security in the authorized ANY-801
worktree. Main base: dab092029043d08ce93d224cd83080f2de825800.
PydanticAI checkpoint: 686ea1553eeea4e08b2cce191123156313e59c65 (all five CI jobs passed).
LiteLLM implementation revision: 8c269d221ff96f1c21091db5bdd8bf17ade484ef.
Local tests began at that checkpoint plus exactly the manifest/lock delta now committed
in 8c269d221ff96f1c21091db5bdd8bf17ade484ef; runtime application sources are unchanged in this continuation.
Later documentation commits do not change the tested runtime tree.

| Package | Original main | Final combined graph |
|---|---|---|
| litellm | 1.89.3 | 1.103.10 |
| pydantic-ai-slim / pydantic-graph | 2.2.0 / 2.2.0 | 2.64.0 / 2.64.0 |
| genai-prices | 0.1.11 | 0.2.1 |
| boto3 / botocore | 1.43.112 / 1.43.112 | 1.43.123 / 1.43.123 |
| h2 / hpack / hyperframe | absent | 4.4.1 / 4.2.0 / 6.1.0 |
| filelock | 4.2.1 | 4.2.1 retained |
| httpx2 / griffelib | 2.13.1 / 2.3.2 | retained |
| openai / pydantic | 2.43.0 / 2.13.4 | retained |

These are all package-version changes. LiteLLM requires boto3>=1.43.117, explaining
its mandatory update and botocore's exact floor. Its httpx[http2] requirement introduces
the three HTTP/2 packages. No Proxy/CLI/provider/tool extras or unrelated upgrades added.
uv 0.11.19 generated the lock; no hand-edited hashes/metadata or forced constraints.
`uv lock --check --no-build --python 3.12` passed. Slim requires Graph exactly 2.64.0.

The filelock<4 conflict belongs to rejected latest candidate LiteLLM 1.106.6. It does
not require waiting for every LiteLLM update: official maintenance release 1.103.10
has no direct filelock constraint and is listed as patched for GHSA-w4c7-34wj-hqm8.
The requested intermediate version resolves with secure filelock and current PydanticAI.
Malicious releases 1.82.7, 1.82.8 and 1.107.0 are excluded and were not executed.

## Artifact assessment and security verdict

Selected deployment wheel: litellm-1.103.10-cp310-abi3-manylinux_2_28_x86_64.whl.
SHA-256: f639bd02ac34869080b7792732336345bc066ffb04be301093090425f6caa2bc.
Live download hash matched; prior 3414 RECORD checks for these exact bytes were reused.
No .pth/sitecustomize/usercustomize or unsafe archive paths. All 2474 packaged Python
files match official tag v1.103.10, resolved commit b3287e3972c7aeb5c8015878a9b035caadf71fb9.
This source comparison is broader than the three-file preliminary check.

PyPI provenance still returns 404. Neither wheel publisher signature nor native binary
reproducibility is verified. Docker signatures are not substituted for wheel provenance.
The bundled litellm/rust_bridge/_native.abi3.so SHA-256 is
bb002af625edfeb47585743ab6f454cbf0d16514d7c1e29e93e574ca4c10f70c;
installed bytes in both final runtime images match it.

Native assessment: reviewed Python loader/configuration/catalog/dispatch/bindings and
Rust build/module-registration sources. Maturin 1.15.0 builds a PyO3 abi3-py310 cdylib
from litellm-rust/crates/python-bridge. build.rs only adds macOS linker flags. Source
module initialization registers documented functions/classes. Static ELF dependencies
are standard libgcc/libpthread/libm/libdl/libc/loader; exports are PyInit__native and
PyInit_pyo3_async_runtimes. ELF .init/.init_array exist; their binary implementation and
Rust transitive compilation are not independently reproduced or certified safe.

get_native_bridge imports the extension lazily. The catalog's completed Responses
path is PYTHON_ONLY, including under configuration overrides; public dispatch returns
through Python before NativeBinding.load. This is the application's existing SDK path.
No component is removed/patched, and no Rust-disable override or bypass was introduced.
The 188-test matrix, expanded unit suite and usage probe observed no native import/map.
This evidence supports isolated execution and review of this SDK upgrade; it does not
approve enabling unrelated native/Proxy/OCR routes or assert whole-binary benignness.

Fresh OSV querybatch covered all 104 registry package/version pairs in the complete
runtime/dev workspace lock: zero advisory matches. Previous LiteLLM advisories no longer
match the selected version. No suppression/ignore list was used. Advisory absence is
not a complete security or malware guarantee.

Changed companion wheel SHA/RECORD/path/startup-hook inspection passed. All are pure
Python, with no native libraries or startup hooks. Every packaged Python file matched
its official tag: boto3 39, botocore 76, h2 12, hpack 8, hyperframe 4. PyPI attestations
were unavailable (404); source/hash matching is not cryptographic publisher verification.

| Changed companion wheel | SHA-256 |
|---|---|
| boto3-1.43.123-py3-none-any.whl | d18d66e1e13faa0c25d0b1b8c5ce946e29fb5fc0b6456b655a93a678ff4cc313 |
| botocore-1.43.123-py3-none-any.whl | e30580f9c1282c321529238ff8ff75066096a2adbd0a293c8ae592c21d1733a3 |
| h2-4.4.1-py3-none-any.whl | 0e25f1462b23c9cb82d9eb02e28bc706dac2a68cb457c6a0d74d63c8a2a5d0e6 |
| hpack-4.2.0-py3-none-any.whl | 858ac0b02280fa582b5080d68db0899c62a80375e0e5413a74970c5e518b6986 |
| hyperframe-6.1.0-py3-none-any.whl | b03380493a519fce58ea5af42e4a42317bf9bd425596f7a0835ffce80f1a42e5 |

Existing Pydantic work is preserved. Exact Slim wheel SHA-256
63ccfe3f66beefb0a2fb3843d471f9d5b74a432f4436ed5ceb7e0d6bb06cb1e4 and Graph
5034949fd78899001b31b819e3fd9357019766d48245f788712bb3a91ccf75a2 retain their
previous pypi-attestations 0.0.30 cryptographic verification constrained to
https://github.com/pydantic/pydantic-ai. genai-prices/httpx2/griffelib provenance
limitations from that checkpoint remain; these artifacts are unchanged in this step.

## Actual verification

Candidate packages were installed only in disposable Docker images using official
apps/api/Dockerfile and its locked installs. No host/ordinary environment install.
Trusted host orchestration creates unique, labelled test resources. Behavioral tests
use synthetic keys and controlled HTTP providers with network none or an internal
Docker network: no provider egress, real env, personal/cloud/SSH directories, production
DB, Docker socket or primary checkout mount. Test fixtures and sanitized sources are
copied into container filesystems. No paid model calls.

188 meaningful regressions passed on installed fresh-image packages (no application
source overlay): gateway Responses bridge, optional diagnostic review, tariff provenance,
translation commercial terms, reply similarity, regeneration/review corrections, SQL
pipeline, optional-review SQL and translation-commercial SQL workflow.
Expanded unit/architecture: 841 passed, one unrelated Node auth interoperability case
deselected locally because host Windows pnpm links are not usable by Linux Node; that
case remains enabled in full repository CI. Counts overlap and are not summed.
Both suites report native module_loaded=false and mapped=false.

| Contract | Observed baseline vs updated result |
|---|---|
| Timeout | 2 gateway-owned physical transport attempts |
| Wrong language then 429 | 3 requests: (1,1), (2,1), (2,2) |
| Provider schema rejection | 1 request; no schema downgrade or unsupported retry |
| Exhausted corrections | bounded 3 semantic attempts |
| Strict output | NativeOutput, required fields, additionalProperties=false |
| Correction context | rejected assistant output plus validator feedback/fence |
| Rejection persistence | correct rejected physical call; transport retry not mislabelled |
| Usage | missing remains unknown in authoritative accounting |
| Diagnostic review off | no additional diagnostic dispatch |
| Diagnostic review on/replay | bounded dispatch; accepted replay does not redispatch |
| SQL | budgets, actual overruns, frozen authority, fencing, restart, publication isolation |

A separate synthetic HTTP probe compared 1.89.3 vs 1.103.10: actual model, response ID,
request ID, input/output/cached/reasoning tokens and unknown reported cost were exactly
equal (37/12/8/3 tokens). LiteLLM's existing encoded response ID format was retained;
an initial probe assumption that the SDK returns the bare provider ID was disproved by
the old-version baseline, so no application behavior or existing test was changed.
Prepared-schema digest sets matched all seven groups against the preceding PydanticAI
checkpoint. The public PydanticAI prepare_messages feedback fix and installed-version
priceSource remain unchanged. No extra LLM review/validation calls were introduced.

Ruff check/format: all 433 backend/API files passed. Linux and win32 mypy: each passed
248 source files. OpenAPI export freshness and frontend api-types check passed.
Independent read-only review found no actionable dependency/code issue.
Full repository CI runs on [PR #62 Checks](https://github.com/gushinets/ScopeCreepGuard/pull/62/checks)
against the proposed merged state; current outcomes are recorded there rather than
representing pending jobs as passes. The preceding Pydantic-only head 686ea15 had all
five CI jobs green before this LiteLLM continuation.

## Fresh official runtime images

Both official API runner and export-worker targets built successfully without Dockerfile
modifications, bounded-build substitutions or source overlays. Worker image is the shared
image used by the llm role. Docker inspect confirmed image IDs and revision labels below;
network-none containers verified exact installed versions and native-file hash.

- scg-any803-10310-api:verification: `sha256:8b02c6796fe978f32f54098d5117d4cfabee0a53ca5e5d61f77c7293b69a3fc2`; revision `8c269d221ff96f1c21091db5bdd8bf17ade484ef`.

- scg-any803-10310-worker:verification: `sha256:956b43dafae8283fb273421ae544e044b8d82dcd7c7e9dd24dd342a4e535df04`; revision `8c269d221ff96f1c21091db5bdd8bf17ade484ef`.

These are component build/package checks, not a claim of full application E2E readiness.
Full readiness additionally needs the documented complete Compose contour, PostgreSQL,
one-shot migrate, API/app/workers, private test object storage and Mailpit, as exercised
by the repository CI smoke checks. No migration or deployment architecture changed.

## Maintenance, unfinished operations and coordinated rollback

Prepared schemas match tested fixtures and the stored-schema equality guard remains.
This is not proof for every possible historical payload. Keep the existing conservative
maintenance sequence: block new enqueue and drain user AND diagnostic lanes using old
compatible images. Confirm no unfinished operations, active leases or unknown outcomes;
do not delete rows or silently replay incompatible schemas. If draining cannot finish,
defer upgrade or retain old compatible workers for operator resolution.

Use the documented README maintenance procedure and existing project name, e.g.
`python scripts/stack.py update --project scopecreepguard` with the deployment's existing
env/image arguments. Keep the one-shot migration gate; API/workers never mutate schemas
at startup. No new DB migration is required for this change. Do not reset databases,
remove existing volumes, prune Docker or stop unrelated services.

Rollback the LiteLLM step to the complete 686ea15 bundle (manifest + lock + compatible
PydanticAI application code + matching rebuilt/API-worker images). For a whole-PR rollback
to main, restore its application code too: package-only PydanticAI downgrade would leave
an incompatible retry-feedback bridge. Stored operation prices remain frozen in either
case. No schema downgrade or operation repricing is introduced.

## Delivery, limitations and evidence

Same branch and PR #62 targeting main; no additional branch/worktree, force-push, merge,
Dependabot edits or Linear writes. The untracked preliminary investigation and unrelated
reports remain untouched/uncommitted. Ignored evidence is under output/any803-litellm-10310/.
Native/wheel cryptographic provenance remains the explicit limitation, not an unresolved
filelock compatibility blocker for the application's tested Python Responses path.
The latest 1.106.6 candidate remains rejected; 1.103.10 completes the selected intermediate
upgrade. Existing closed/unmerged Dependabot #58 (older LiteLLM 1.100.4) and #59 (older Slim
2.53.0) are superseded by this combined PR, not merged or modified.

Sources: [release metadata](https://pypi.org/pypi/litellm/1.103.10/json),
[official source](https://github.com/BerriAI/litellm/tree/b3287e3972c7aeb5c8015878a9b035caadf71fb9),
[patched maintenance release advisory](https://github.com/BerriAI/litellm/security/advisories/GHSA-w4c7-34wj-hqm8).
