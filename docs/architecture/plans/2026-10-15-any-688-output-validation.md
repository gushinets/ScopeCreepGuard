# ANY-688: AI output validation implementation plan

> Execute inline using Superpowers executing-plans and test-driven-development. The user explicitly requires this checkout, no brainstorming, no worktree, no commit/push/PR/Linear changes, and continuation after planning.

**Goal:** Reject scope reversals, foreign generated prose, cosmetic regeneration and unsupported delivery commitments without changing accepted facts or losing saved edits.

**Architecture:** Keep the durable ANY-663 worker, ProviderGateway, LiteLLM and PydanticAI NativeOutput. Use local Lingua fragment evidence for input selection and separate strict output checks; local equality/cosmetic checks handle obvious duplicates. Add one structured semantic review per locally valid material candidate, with its own durable step and the same operation ledger/deadline/budget. A review never repairs or recursively reviews itself. Generator correction remains bounded to three candidates for the failed stage.

**Tech stack:** Existing pinned Python/PydanticAI/Lingua/PostgreSQL/Next.js; no dependency or schema migration planned.

**Spec:** ANY-688 Linear description and the current user requirements; reproductions F1/F3/F7/F8 in `docs/architecture/2026-10-15-repository-ticket-review.md`. Inherit all three ANY-663 plans in this directory.

**Base/branch:** Verified local and origin ANY-663 head `4450ecacc89f7fd67fc62cdaf3bdc740dc4988cb`, tree `b98addef87889fa5fc02f4ec9d6249e49e74a3f5`; recorded origin/main `f00e101` has the same tree. New branch `codex/any-688-output-validation` in the current checkout, no history rewrite. Initial shell proxy failure was resolved through approved read-only access; git ls-remote confirmed both remote heads before implementation. Preserve .gitignore, the untracked review/design documents and ignored AGENT/WORKLOG.

## Constraints and validation decisions

- Original request, URLs, email addresses and code are passed unchanged. Only derived detection text removes neutral spans. Select a confident dominant language using substantive independently scored fragments and their relative letter volume, falling back to interface language with existing uncertain status. Explicit override wins. Selection remains frozen with requestHash/operation inputs; existing reset, reload and History restoration remain authoritative.
- Analysis prose uses interface language; client replies and every document field/label use selected client language. Check confident foreign sentences/spans independently, even if small relative to the output. Only verified scope citations, source-grounded names, URLs/emails and code identifiers are exceptions; quoted arbitrary foreign prose is not. Preserve the existing contextual short-label vocabulary policy. Uncertain prose corrects/fails.
- Local deterministic guards retain numerical/unit/currency preservation and whitespace equality. Reject text that retains the previous reply with superficial greeting/thanks/punctuation changes. This is a conservative textual screen, not proof of semantic novelty.
- Structured semantic review sees frozen accepted analysis, scope/request, saved commercial/material context and actual candidate as untrusted data. It checks all verdicts, unauthorized inclusion/free-work, conditional proposals, explicit saved decisions, absolute/relative localized delivery commitments and cosmetic formulation. Customer wishes and project endDate alone do not authorize new promises. Manual saved values remain authoritative. Decision schema forbids extras; each rejected/uncertain decision identifies an actual field plus enumerated rule and bounded repair instruction. Malformed/uncertain reviews fail closed; no alternate target language.
- Reviews use ProviderGateway and existing SQL steps/provider_calls, one semantic attempt and at most the existing two gateway transport attempts. Preallocate per-stage review slots for candidates 1–3. Persist/reuse decision by candidate+context hash after restart. Rejected generator calls retain usage/cost and concrete feedback. No accepted stage is regenerated. Existing physical limits stay check=12, translate=8, regenerate=6, estimate=6; semantic reviews consume these limits, so correction may stop earlier. Minimum admission reserves now include reviews. No spending/deadline increase.
- Bump prompt/validation implementation version to workflow-v4. Pending v1–v3 operations fail workflowVersionUnavailable before dispatch/reuse; completed results remain readable. Operators drain old workers if pending work must finish. Never rewrite versions, checkpoints or counters.
- Legacy activation/persistence findings F2/F4/F5/F6 are excluded. Validate the intended workflow_v2 + llm_workflow runtime and explicitly report unavailable configuration. No application database migration or customer data.

## Ordered tasks and verification

### 1. Input and output language

- [x] Add fixtures in `backend/tests/unit/test_any688_validation.py`: RU/EN interface; RU/EN/ES; dominant mixed RU/EN; technical terms; neutral/ambiguous/override; preserved URL/email/code; verified citation/names; EN→RU, RU→EN, ES→EN standalone sentence regressions.
- [x] Run these against the existing validators and observe the missing-behavior failures.
- [x] Modify `integrations/llm/detection.py` to expose derived input dominance and strict foreign-span checks. Integrate in `stages.py` without weakening `label_evidence`. Verify existing EN/RU/ES labels and detector regressions.

### 2. Scope, deadlines and novelty

- [x] Add failing local cosmetic and structured-review tests, using actual stage runner and ProviderGateway with controlled transport, covering F1/F7/F8 and localized equivalents, in_scope/borderline/out_of_scope, saved free-work decisions, tentative/conditional dates and unconditional promises.
- [x] Add focused `integrations/llm/semantic_review.py` containing strict decision types, review instructions, persisted review runner, and deterministic cosmetic screen. Connect review to locally accepted generator candidates, including resumed checkpoints, through `stages.py`.
- [x] Add review slots/minimum call accounting in `services/llm/operations.py`; preserve existing physical/time/money caps. Reuse `LlmSQLStore` step hashing, acceptance/checkpoint/accounting. Version in `domain/llm/runtime.py`; extend stage prompts with authoritative language, conditional commitments and concrete novelty rules.
- [x] Verify native schema decisions, invalid decision fail-closed, concrete correction feedback, one-stage-only correction, exhaustion preserving saved input, review recovery and accounting of rejected/uncertain calls.

### 3. Integration and browser acceptance

- [x] Adapt controlled provider fixtures to respond to semantic-review schemas; add SQL integration regressions for correction/exhaustion/accounting, accepted-stage reuse, pending-v3 rejection and preservation of manual values. Use ONLY the disposable PostgreSQL fixture.
- [x] Run backend unit/API/architecture and relevant PostgreSQL suites, Ruff/format/Mypy; affected frontend tests, TypeScript/lint, contract freshness. Read installed Next.js guide before any frontend code changes.
- [x] Predefine 12 synthetic scenarios: EN/EN Arrow; RU/RU Arrow; RU/ES Instagram; EN/RU; RU/EN; dominant RU technical+URL/email; dominant EN mixed; ambiguous fallback; explicit override; scope reversal/free-work correction; deadline correction/conditional alternative; cosmetic regeneration. Repeat each core generation three times; one saved check gets five sequential regenerations. Also exercise language replacement, manual edit cancel/confirm, reload/History, CO/Copy/PDF.
- [x] Through actual browser UI verify frontend/API/LLM-worker/model/prompt version. Prefer a disposable controlled-provider stack for repeatability. Distinguish controlled fixtures from real model observations. Report deviations immediately with scenario, operation ID, expectation/actual and reproducibility; stop sequences that compound damage/cost, fix and rerun retaining evidence.
- [x] Before any live call, estimate baseline 3 generation calls + 2 reviews = 5/check (36 core runs = 180 minimum, beyond prior 24-call authorization); one regeneration requires 2 minimum calls (five = 10). Shared live limits: at most 24 physical calls including reviews/retries, 15 minutes, and the smaller of configured authorized spend and USD 1; no new tariff/model assumption or limit increase. Refuse live dispatch without configured valid bounds. Run deterministic coverage and only a bounded live subset if configured; unexecuted matrix remains explicitly unexecuted.
- [x] Collect scenario table with runs, first-attempt valid, corrected, terminal failures, invalid results published, cosmetic variants accepted, calls, latency and cost. Unknown observations stay unknown. Browser synthetic evidence in ignored `output/any-688/`.

### 4. Handoff

- [x] Review final diff against every requirement; update this execution record and a verification report with measured sample sizes, test results and rollout/verification limits. Update ignored AGENT.md/WORKLOG.md with actual measured machine interval (start measurement 2026-10-15 13:24:34 UTC, initial discovery before that excluded); human/billable effort unknown.
- [x] Recheck preserved local files, branch/base and Git status. Leave changes uncommitted.

## Initial verification limits

Docker socket access is currently denied in the sandbox; retry read-only availability through the approved tool escalation before declaring PostgreSQL/browser integration unavailable. Shell remote access is blocked by its proxy. Existing ANY-663 record reported no usable tariff for configured gpt-5.6-luna; inspect safe configuration presence without exposing credentials. Do not substitute defaults or migrate the application database to make tests pass. The semantic reviewer is probabilistic and can miss violations; controlled tests establish behavior for fixtures, not infallibility or real-model accuracy.


## Execution record

Implemented inline on the verified base without worktree, history rewrite, commits,
push/PR or Linear changes. No dependency/schema/API contract changes. No frontend
source changes; dev-generated next-env references were restored after browser work.
Checked tasks above are completed within the explicit verification limits below.

Final evidence: [ANY-688 verification](../any-688-verification.md). Combined backend
unit/API/architecture + affected disposable PostgreSQL/API: 539 passed /104.08s.
Final focused multilingual/review suite: 61 passed /19.10s, including later added
uncertain/timeout and all RU/EN/ES foreign-sentence pairs (overlaps combined suite).
SQL pipeline with actual manual reply/fee/effort/currency edits before exhaustion:
7 passed /49.88s. Frontend334 /47files /45.20s; Ruff/format314, both Mypy199,
TypeScript including restored generated references, ESLint (one existing warning),
OpenAPI/generated contract freshness and diff whitespace passed.

Actual browser: 12 scenarios x3 core generations =36 checks,185 controlled physical
calls. Follow-ups: five sequential regenerations, three override/translation runs,
and a new-request reset check. Overall45 successful operations/213 controlled
calls; four rejected candidates corrected, no observed wrong-language/scope/
commitment/cosmetic result published. Manual cancel/reload and fee/effort preservation,
History reopen/restoration and Copy passed. PDF browser export unexecuted: separate
object storage/export worker absent. Late detector calibration/review prompt
clarifications were covered on final code by automated tests, not a repeated full
browser matrix. Browser model and review decisions were controlled HTTP fixtures,
not real-model observations. No live calls: ordinary local flags off and configured
gpt-5.6-luna lacks usable tariff/operator bounds. The full live matrix exceeds the
inherited24-call cap; real accuracy/latency/cost remain unknown.

A browser translation transport was suspended before admission; no operation/calls
for that failed transport, edits survived. Disclosed during execution; reload
recovery and explicit retries succeeded without duplicate History. Automation
selector, Windows event-loop/origin setup and denied temporary-folder failures were
resolved as test setup issues. Browser-close automatic review timed out once;
authorized retry succeeded. The remaining owned test container was verified by
immutable ID,label,12 synthetic projects and45 operations before removal. Application
DB untouched. Preserved local file hashes match discovery.

Measured machine elapsed:2026-10-15 13:24:34–14:49:36UTC /
16:24:34–17:49:36MSK,5102seconds (1h25m02s), through final verification and
owned infrastructure cleanup. Includes tool/approval waits and transport suspension;
initial discovery and final bookkeeping after that endpoint excluded. Human labor,
active CPU time and billable hours unknown. Updated ignored AGENT/WORKLOG.

Rollout owner: coordinate matching v4 API/frontend/LLM worker on existing0005 schema,
valid provider bounds/model and flags. Drain older pending work with its original
worker if required; v4 rejects v1–v3 pending rather than silently resuming. Validate
real model quality under available explicit budgets. Legacy/persistence/export
activation remains outside ANY-688.
