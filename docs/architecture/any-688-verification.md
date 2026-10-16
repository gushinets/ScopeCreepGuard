# ANY-688 verification and handoff

# Follow-up verification

The remaining acceptance corrections and final deterministic/browser evidence are
recorded in [16 October verification](2026-10-16-acceptance-verification.md).
The original record below describes its own earlier version and limits; do not
apply its build, totals, prompt version or PDF limitations to the follow-up.

15 October 2026. Implementation remains uncommitted on `codex/any-688-output-validation`.

## Base and changes

Verified base: `4450ecacc89f7fd67fc62cdaf3bdc740dc4988cb`, the latest remote
`codex/any-663-llm-workflow` head, confirmed with `git ls-remote`. Recorded remote
main `f00e1014c376cba9e5dc65e73421a98c3aa3c37e` has the same committed tree
`b98addef87889fa5fc02f4ec9d6249e49e74a3f5`. Current checkout, new branch, no
worktree or history rewrite. The original `.gitignore`, review document and local
design files are preserved. No commits, pushes, PRs, Linear mutations or application
database migrations.

Implementation record: [plan](plans/2026-10-15-any-688-output-validation.md).

- `integrations/llm/detection.py`: original request stays intact. Derived input
  text excludes URLs, emails, code identifiers and a finite calibrated vocabulary
  of technical nouns/product names. Independently scored substantive sentences/
  Lingua spans and letter volume determine dominance. Input confidence 0.75,
  margin 0.20, dominant share 0.65; uncertain volume remains in the denominator.
  Output uses the existing 0.80 policy plus independent foreign sentence/span
  checks (minimum eight letters), regardless of majority language. These are
  empirical defaults, not measured accuracy guarantees. Detection version is
  `lingua-2.1.1-input-v2-output-v2`.
- `integrations/llm/stages.py`: strict actual-language checks precede semantic
  review; only verified scope citations may be exempted. Existing contextual
  EN/RU/ES label handling remains. Whitespace duplicates remain rejected, with
  additional conservative framing/punctuation/thanks checks. Schedule-shaped
  numbers go to contextual review while amount/unit/currency checks remain local.
- New `integrations/llm/semantic_review.py`: one structured review per locally
  valid material candidate. Actual messages, all verdicts, conditions, saved
  concessions, relative/absolute promises, facts and cosmetic changes are reviewed
  against frozen context. Candidate/source text is untrusted data. Strict native
  decisions reject extra fields, inconsistent verdicts and nonexistent field paths.
  Feedback uses canonical field/rule instructions rather than forwarding arbitrary
  model-authored text into the generator or technical logs. Uncertain decisions
  correct/fail; malformed decisions fail with existing `providerOutputIncomplete`
  and `review.structure` feedback. The reviewer has no repair/review recursion.
- `services/llm/operations.py`: preallocate three review slots per material stage
  in existing `llm_steps`; no schema changes. Minimum calls are check=5,
  translation=4, regeneration/estimate=2. Existing physical caps remain 12/8/6/6,
  operation deadline 180 seconds and configured monetary ceiling unchanged.
  Every review uses ProviderGateway and the same reservations, accounting, lease
  and deadline. A review has one semantic attempt, at most two transport attempts.
  Slots not executed consume no calls; their pending status does not prevent a
  completed operation from being terminal.
- `domain/llm/runtime.py` and stage prompts: `workflow-v4` pins changed prompts
  and validation. Pending v1–v3 work fails before dispatch/accepted-stage reuse;
  completed old results stay readable. Reviews and accepted judgments are bound
  to candidate/context hashes and reused after recovery. Estimate refresh remains
  authorized to change preliminary estimates under frozen current commercial
  inputs; publication still preserves manual values independently.
- Tests: new `test_any688_validation.py`, `test_any688_semantic_review.py` and
  controlled ledger fixture; updated review-correction/language/pipeline suites.

The smallest adequate combination selected here is local language/numerical/
obvious-duplicate screening plus structured contextual review. A phrase denylist
does not decide scope, conditional promises or saved concessions. Semantic review
is probabilistic, including when the same configured model performs generation
and review. No claim of infallibility or semantic novelty proved by similarity.

## Automated verification

| Check | Result |
| --- | --- |
| Combined backend unit/API/architecture + affected disposable PostgreSQL/API integration | **539 passed, 104.08 s** |
| Final multilingual/review suite, including subsequently added uncertainty/timeout and localized cases | **61 passed, 19.10 s** (overlaps the combined run; do not add totals) |
| SQL pipeline rerun with actual manually edited reply/fee/effort/currency before exhaustion | **7 passed, 49.88 s** |
| Frontend Vitest | **334 passed, 47 files, 45.20 s** |
| Ruff lint / format | Passed; **314 files formatted** |
| Mypy, normal and Windows platforms | Passed; **199 source files** |
| Frontend TypeScript | Passed, including after restoring dev-generated type references |
| Frontend ESLint | No errors; existing unused `_s` warning in `lib/llm/schema.test.ts` |
| OpenAPI and generated frontend contract freshness | Passed; no public contract change |
| Diff whitespace | Passed |

The first local test pass was intentionally red: foreign standalone sentences,
cosmetic suffixes and both semantic reproductions were accepted by the old runner.
Positive fixtures also exposed the old false rejection of conditional tomorrow/
mañana/завтра and saved free concessions. Further calibration found short Russian
technical input and a regional Babel locale edge case; both are corrected with
regressions. A sandboxed broad run could not use its owned temp directories and
did not pass; the approved rerun passed. These setup errors are not product failures.

Coverage includes RU/EN interface, RU/EN/ES requests, mixed dominance, uncertainty,
override, unchanged original URLs/emails/code, names/verified quotes/contextual
labels, foreign sentences, all verdicts, localized absolute/relative promises,
conditional alternatives, equality/whitespace/cosmetic rejection, malformed/
uncertain review, rejected/unknown accounting, recovery/hash binding, accepted
stage reuse, optimistic publication and manual material preservation on exhaustion.
Structured decisions in these tests are controlled, not evidence of a real
reviewer's judgment accuracy.

## Actual browser: controlled provider only

Actual Next.js UI, authenticated synthetic account/projects, real API, real
`LlmWorker`, PostgreSQL, PydanticAI NativeOutput, ProviderGateway and LiteLLM with
controlled HTTP responses. Worker identity `any688-controlled-worker`; requested/
reported model `gpt-5.4-nano` is a fixture label, not a live model invocation.
Runtime `workflow_v2 + llm_workflow`, prompt/validation `workflow-v4`.

Twelve predefined scenarios each completed three core generation runs. The
reported bad scope/deadline/foreign sentence was injected on the first run of
S10/S11/S12 respectively; the other two runs used valid controlled output.
All three tones were checked in completed scripted loops, with initial baseline
screens also inspected. CO previews were visually inspected in EN and RU/ES.

Latency below is mean operation admission-to-terminal time in this controlled
stack, including worker polling. It excludes pre-admission language detection,
UI rendering and confirmation time. It is **not real-model latency**. Calls are
controlled physical gateway/HTTP attempts including reviews; external calls are
zero. Real-provider cost is **unknown**, not a zero-cost accuracy/performance claim.

| Scenario | Runs | First-attempt valid | Corrected successfully | Terminal failures | Wrong-language results published | Scope/commitment violations published | Cosmetic variants accepted | Calls | Latency | Estimated/known cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| S01 EN UI / EN Arrow + email | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 2.908 s | Unknown real-provider |
| S02 RU UI / RU Arrow + email | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 1.898 s | Unknown real-provider |
| S03 RU UI / ES Instagram + Facebook | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 2.959 s | Unknown real-provider |
| S04 EN UI / RU client | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 2.510 s | Unknown real-provider |
| S05 RU UI / EN client | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 2.510 s | Unknown real-provider |
| S06 EN UI / dominant RU, technical terms, URL/email/code | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 1.921 s | Unknown real-provider |
| S07 RU UI / dominant EN mixed request | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 3.283 s | Unknown real-provider |
| S08 RU UI / neutral input fallback | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 2.423 s | Unknown real-provider |
| S09 EN UI / ambiguous mixed input fallback | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 15 | 3.152 s | Unknown real-provider |
| S10 Scope reversal / unauthorized free work | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 17 | 3.267 s | Unknown real-provider |
| S11 Unsupported next-week delivery | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 17 | 3.234 s | Unknown real-provider |
| S12 EN output with Russian final sentence | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 16 | 3.282 s | Unknown real-provider |
| Five sequential regenerations of saved S12 | 5 | 4 | 1 | 0 | 0 | 0 | 0 | 11 | 1.438 s | Unknown real-provider |
| Manual language override / recovery / reload | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 12 | 1.634 s | Unknown real-provider |
| New Russian request resets Spanish override | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 3.139 s | Unknown real-provider |

Totals: **36 core checks / 185 controlled calls**; with follow-ups,
**45 successful operations / 213 controlled calls**, four rejected generator
candidates corrected. The fixture ledger simulated USD 0.03195 using synthetic
rates/usage; it is not paid spend or a provider cost estimate. Copy reply/CO,
cancelled manual replacement, confirmed language replacement, saved manual fee
333.00 and effort 9.5, reload, History reopen and selection restoration passed.
S12 had exactly three archived checks after regeneration/translation; the later
intentional new-request check created its fourth. No duplicate History observed.

### Deviations and disposition

- Browser automation initially used an incorrect Russian tone label; operation
  succeeded, script paused. Corrected selector and continued the remaining runs.
- Translation POST hit `ERR_NETWORK_IO_SUSPENDED` before API admission: no operation
  reference and no provider calls for that failed transport. Disclosed during
  execution. Manual values/reply survived. Reload recovery created successful
  operation `e700c911-2aec-40d0-bfa6-adbdcb556063`; an explicit additional Apply
  produced `82da703d-f539-41da-bca0-8070f51f68a3`. These were separate operations,
  both accounted; neither added History. The third override run verified reload
  and new-request reset. Before/after synthetic screenshots and metrics retained.
- No invalid language/scope/commitment result, accepted cosmetic variant, lost
  saved edit or duplicate History was observed in the completed matrix. Terminal
  correction failures and retained manual edits are covered separately in SQL.
- PDF download was **not exercised through UI**: durable PDF export requires
  finalized agreement, configured object storage and export worker; that separate
  runtime was not configured in the isolated LLM stack. Existing automated PDF
  paths passed within the backend suites; no new visual PDF acceptance claim.
- Browser ran the initial v4 implementation; later short-technical input/Babel
  calibration and review-instruction clarifications were verified on the final
  tree by automated tests, not by restarting/repeating the entire browser matrix.
- Cleanup permission review timed out once, then the authorized retry succeeded.

## Live-test limits and rollout

Live calls: **0**. Safe configuration inspection found both workflow flags false,
worker role `exports`, key present (never printed), model `gpt-5.6-luna`, and no
usable local tariff/operator input/output bounds. Thus the intended workflow is
not activated in the ordinary local configuration. No provider/model/price defaults
were substituted and no deployment configuration was changed.

Before any live testing the plan estimated at least 180 calls for 36 core checks,
plus 10 minimum for five regenerations, already exceeding the inherited **24-call**
authorization. Shared live limits were at most 24 calls, 15 minutes and the smaller
of existing authorized spend or USD 1, including reviews/retries. Missing valid
bounds prevented even a bounded live subset. Real-model first-attempt validity,
review false acceptance/rejection, latency, tokens and monetary cost remain unknown.
The entire real-model matrix is unexecuted.

Operator owns coordinated frontend/API/LLM-worker activation on the existing
0005 schema, a valid model and conservative tariff/bounds. Drain v1–v3 pending work
under its original worker if it must finish; otherwise new worker fails it explicitly.
Do not rewrite versions/reset budgets. Deploy matched v4 code; reviews consume the
existing caps and can cause earlier bounded exhaustion. Run real RU/EN/ES review
calibration under separately available configuration/authorization before acceptance
claims about actual model quality. Legacy activation/persistence/export findings
remain separate tickets.

Measured machine elapsed interval: **13:24:34–14:49:36 UTC / 16:24:34–17:49:36 MSK**,
**5,102 seconds (1 h 25 min 2 s)** through final verification and owned test-stack cleanup. Includes tool waits,
transport suspension and the long automatic-review timeout; initial discovery and
subsequent handoff bookkeeping are excluded. Active CPU time, human labor and
billable hours were not measured and must not be inferred from this interval.
