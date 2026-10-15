# ANY-663 review corrections implementation plan

> Execute inline with `superpowers:executing-plans`, using failing regressions before fixes. The user authorizes implementation now; no approval pause, brainstorming, branch changes or commits.

**Goal:** Fix contextual document-label validation, restore stage-specific tone/commercial prompts, and reject unchanged regenerated replies.

**Base/branch:** Current `de9c511`, `codex/any-663-llm-workflow`, existing checkout. Preserve `.gitignore` and the two local design files. No worktree, rebase, paid calls, application migrations, push, PR or Linear changes.

**Architecture/stack:** Keep ProviderGateway → LiteLLM Responses → PydanticAI NativeOutput, persisted stages/call accounting and existing bounded corrections. No dependency, API or schema changes. The user's attached review request is the specification; the original ANY-663 plan remains historical context.

## Review focus

- Short foreign labels must not inherit a confident target-language group.
- Long ancillary label prose and ordinary analysis/replies must retain strict detection.
- Section numbers in realistic headings are document structure, not new commercial amounts.
- Pending version-v1 work must not consume changed v2 prompts or validations.
- Duplicate correction/exhaustion must preserve the old Draft, analysis, CO and call ledger.

## Ordered changes

1. **Labels:** Add realistic EN/RU/ES fixture labels and runner regressions. In `stages.py`, use a label-only contextual strategy for concise uncertain labels, with independent confident foreign-label/span rejection before grouped evidence. Keep nonempty fields, strict long prose, existing detector confidence thresholds, exclusions and target. Ignore only structural heading-number prefixes in numerical checks. Test ambiguous legitimate headings, foreign/mixed labels and strict ordinary prose; verify a valid Change Order needs one call. The final review tightened contextual borrowing: uncertain headings must consist of vocabulary from the existing reviewed target-language document catalog or Babel hour units; a strong group alone is insufficient. Unsupported uncertain headings require correction rather than guessing.
2. **Prompt composition/versioning:** Add explicit `prompts/workflow_v2.py` stage composition, reusing detailed `REPLY_TONE_SKILLS` while removing its plain-text-only suffix in field context. Preserve existing hourly/fixed-fee, missing-data, preliminary estimate and draft-disclaimer rules without a new formula. Analysis gets classification/estimation; replies get all tones; regeneration gets the selected tone; translation gets preservation rules; CO gets document/disclaimer rules; estimate gets commercial rules. Test actual stage requests for relevant rules, language, native schema and absence of conflicting/unrelated instructions. Introduce one shared persisted prompt version `workflow-v2` in domain runtime, admission, repository and worker. Old pending versions fail explicitly before new calls (including when stages were accepted); completed old results remain readable. No migration or counter reset.
3. **Regeneration:** Compare normalized whitespace of the reply candidate with the frozen selected-tone previous text. Raise a concrete `text.unchanged_reply` error through ModelRetry; keep rejected attempts accounted and retry only reply. Test unchanged→revised, whitespace-only, exhaustion, saved-content preservation and no analysis/CO calls. Adapt prior pipeline doubles to produce distinct regenerated wording.
4. **Verification/handoff:** Run focused native-runner/language/prompt tests, affected legacy prompt tests, disposable-PostgreSQL pipeline/worker/API tests, affected frontend regressions, Ruff and both Mypy/TypeScript checks. No live calls. Record exact outcomes and version compatibility here and in ignored AGENT/WORKLOG, with measured machine elapsed separated from unknown human effort. Leave all corrections uncommitted.

## Execution and compatibility

All three corrections are implemented without dependencies, schema/API changes or
edits to the frozen legacy prompt templates. `workflow_v2.py` uses explicit shared,
classification, estimation, document, translation and per-tone sections; the
existing project-timing helper supplies the same frozen timing inputs. New
admission/run/step metadata records `workflow-v2`. A v1 pending step fails with
`workflowVersionUnavailable` before dispatch or accepted-result reuse; finished
v1 results remain readable. Drain the old worker before activation if old pending
commands must finish; never rewrite checkpoints, reset budgets or silently change
the prompt behind an existing key. No migration is necessary.

The selected-tone previous text is already frozen in `document.reply.text`; this
includes saved manual edits. The comparison collapses Unicode whitespace and
rejects unchanged text with `text.unchanged_reply`. Existing ModelRetry, gateway
and SQL feedback/accounting paths handle all attempts; there is no second judge,
analysis rerun or Change Order regeneration. Textual comparison does not prove
semantic novelty.

Label policy preserves normal 0.80 confidence / 0.20 margin / 0.75 dominance and
12-letter prose defaults. Only concise labels inspect shorter independent text.
Foreign evidence, including independently classified spans, blocks group fallback.
An initial label-only target-support screen of 5% of the leading score avoids
mistaking ambiguity between foreign languages for support of the target. It is
tunable, not an accuracy claim. Contextual borrowing additionally requires at
most eight words/100 characters and reviewed target vocabulary. Introduction and
outside-scope ancillary sentences remain strict prose. Known names, URLs and
verbatim citations retain the existing exclusions; required labels stay nonempty.
Unfamiliar uncertain wording may need correction, especially languages without a
built-in reviewed label catalog. It is not published merely because its group
is in the target language.

Fresh-context review found one Important issue in the first label correction:
`Payment / Pago`, `Date de signature`, `Additional terms y fecha` and
`Schedule impact y fecha` could still borrow English group confidence. Those four
reproductions failed before the vocabulary restriction and pass afterward.
No second review loop or new product scope was introduced.

## Verification evidence (2026-10-15)

- Focused real-PydanticAI runner/language/gateway tests: **53 passed in 28.12 s**.
  These use controlled provider responses, not real-model output. Realistic
  EN/RU/ES label sets need exactly one call. Duplicate→revision and whitespace
  cases need two reply-only calls; three duplicates exhaust corrections with
  rejected attempts retained. Source materials remain unchanged on failure.
- Frontend affected tests: **7 files, 54 passed in 27.30 s**. Command from
  `frontend/`: `corepack pnpm test --maxWorkers=2
  components/scope-guard/client-language.test.tsx lib/drafts/autosave.test.ts
  lib/drafts/operations.test.ts lib/drafts/workflow-client.test.ts
  tests/generation-baseline/prompt.test.ts
  tests/generation-baseline/regenerate-request.test.ts
  lib/change-order/estimate-prompt.test.ts`. `corepack pnpm exec tsc --noEmit`
  passed. No frontend source changed.
- From repository root, `.venv/Scripts/python.exe -m ruff check backend apps`
  passed; `-m ruff format --check backend apps` passed, **310 files**.
  `-m mypy backend/src apps/api/src apps/worker` and the same with
  `--platform win32` both passed, **198 source files**. Existing untyped-function
  notes are informational. A narrower Ruff invocation inferred different source
  roots and reported baseline imports; no unrelated cleanup was applied.
- Broader unit runs initially hit the host's denied shared pytest temp, then a
  missing owned parent directory (368/371 passed with six setup errors each).
  These runs are not described as passed. The prepared-parent rerun passed
  **377 tests in 56.34 s**, before the four final-review regressions were added.
  Final corrected-tree command from `backend/`,
  `../.venv/Scripts/python.exe -m pytest tests/unit -q --tb=short -p no:cacheprovider
  --basetemp <fresh-directory-under-the-prepared-owned-review-parent>`:
  **381 passed in 60.97 s**. This includes original compatibility/prompt regressions
  and the four new mixed-label cases.
- Docker availability command `docker version --format '{{.Server.Version}}'`
  failed because `dockerDesktopLinuxEngine` is absent. The eight PostgreSQL
  pipeline/worker/workflow/API tests were **collected only**, not executed or
  passed. Added persistence/accounting/version scenarios therefore remain
  unverified on PostgreSQL here. No application DB was accessed or migrated.
- No paid or live provider calls. No commits, push, PR, rebase, branch switch or
  Linear updates. Unrelated `.gitignore` and both local design-file hashes match
  their pre-change values; index remains empty.

**Measured machine interval:** 2026-10-15 10:13:55–10:35:21 UTC
(13:13:55–13:35:21 MSK), 1,286 seconds / 21 min 26 s through final runtime checks.
Includes tool/test waits and the brief interruption; human labor, human breaks
and billable effort were not measured. Final bookkeeping/status checks after
that endpoint are excluded. Ignored AGENT/WORKLOG receive the same distinction.
