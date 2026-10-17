# Scope assessment and client-language regression repair

## Baseline and historical reference

Repair branch: `codex/restore-scope-assessment-and-language`.
Base: freshly fetched `origin/main` at `3084c1049432ccfa8996b3c9bde10b9ecaaa3fc6`.
Original checkout: `codex/regeneration-current-commercial-terms` at
`9c01aa417570d17f58189e744b08e247a830502c`.

Main does not contain original commercial-terms commit `9c07515` by ancestry.
`git range-diff d3544de..9c01aa4 d3544de..origin/main` proves its two fixes are
identical rebased patches `bbadc7d` and `3084c10`; `git diff 9c01aa4 origin/main`
is empty. The requested branch was created from this verified current main.
All eight pre-existing untracked documents were preserved. No worktree, reset,
stash, staging, commit, push, PR or Linear mutation occurred.

Historical reference: `29c67f4580bea8a7d58530beaeea2abb537af1a9`, parent of
`336571752f3811ed8af084bfa6e9e000996bc42c`. Inspected its result panel and
estimation/Change Order presentation, compared the regression, then traced
frontend types/schema, persistent result projection and History restore,
backend AnalysisStage, classification/estimation prompts, worker publication,
domain normalization/serialization, and API AnalysisSnapshot.
Installed Next.js `use-client.md` was read before frontend edits.

## Recovery findings

| Lost functionality | Root cause | Restored behavior | Verification |
| --- | --- | --- | --- |
| Scope comparison, justification, supporting scope evidence, recommendation | Historical result panel rendered reasoning/citations/suggestion; regression deleted the section, although all values remained in generated and stored analysis | Original interface-language analysis renders again, with verbatim scope quotations and next step; request and summary make the requested change visible | Result/component tests, translated-material tests, saved-store reopening, Russian/English browser screenshots |
| Preliminary additional-work hours and cost in the result experience | Previously exposed through ChangeOrder; on-demand preparation moved classification estimates into `result.estimate` while removing their immediate presentation | Read-only additional-work assessment uses `estimate`; historical analyses may use their original `result.changeOrder` numeric estimate. It never reads the editable saved agreement | Current/historical estimate tests; free-work and cleared agreement terms differ without altering assessment; database snapshot checks |
| English default client reply for typo request in Russian UI | Detector returned English at 0.4078/uncertain, but selector allowed only status=detected and substituted UI locale | Valid override, supported leading candidate even if uncertain, then documented UI-locale fallback only without evidence; invalid locale falls back to English | Actual Lingua reproduction; native runner/provider payload matrix; new-analysis browser check |
| Independent language across new requests | Existing contract already persisted explicit overrides for the same request, reset override on changed request, and sent automatic language only as evidence | Contract retained; automatic selections are omitted from new-analysis overrides and recalculated; new Russian request replaces obsolete Spanish selection | Persistent-store payload tests; selector admission test; browser/new operation payload records |

Verdict/confidence/summary were already retained and remain visible through the
existing VerdictBanner. No assessment schema, API field, migration or mandatory
model field was added. No assessment data was being lost by current mapping or
serialization; both retained `estimate` and analysis text. Existing prompts already
target interface locale for analysis and selected client language for materials;
new tests verify the actual messages passed through the native provider gateway.

Agreement description, schedule prose, rationale, disclaimer and editable terms
remain part of explicit agreement preparation. They are not silently generated
by displaying an assessment. Historical client-language document prose is not
shown as interface-language analysis. Project-context clutter and technical
validator warnings were not restored. Diagnostics stay internal and nonblocking.

## Changed files

- `backend/src/scope_guard/integrations/llm/detection.py`: selection priority, diagnostic version and fallback documentation.
- `backend/tests/unit/test_scope_assessment_language.py`: actual provider messages/targets, typo, uncertainty, overrides, fallback and fresh request selection.
- `backend/tests/unit/test_any688_validation.py`: replace obsolete uncertain-candidate fallback expectation, retaining no-evidence fallback coverage.
- `frontend/components/scope-guard/scope-assessment.tsx`: complete read-only assessment, existing verdict component and historical numeric estimate compatibility.
- `frontend/components/scope-guard/result-panel.tsx`: render assessment from original result before client materials.
- `frontend/components/scope-guard/scope-assessment.test.tsx`: full contents, locales, optional data, historical estimates and translation isolation.
- `frontend/components/scope-guard/nonblocking-result.test.tsx`: replace absence assertion, retain explicit-action/failure coverage.
- `frontend/components/scope-guard/client-language.test.tsx`: retain assessment across translation and reopening.
- `frontend/components/scope-guard/persistent-store.test.tsx`: saved/reopened estimate separation, cleared/free terms, intentional override payloads.
- `frontend/messages/en.json`, `frontend/messages/ru.json`: request, recommendation and preliminary-estimate labels.
- `docs/architecture/plans/2026-10-18-restore-scope-assessment-and-language.md`: implementation record.
- This report. Ignored local `AGENT.md`/`WORKLOG.md` updated separately.

## Focused checks

- Frontend: `node node_modules/vitest/vitest.mjs run` with nonblocking-result,
  scope-assessment, persistent-store, persistent-history, client-language,
  client-reply, change-order, client-material-storage, drafts/validation and
  llm/schema tests: **83 passed**. After adding two override-payload cases,
  reran persistent-store: **25 passed**. **85 unique tests** covered overall.
- Backend: `.venv/Scripts/python.exe -m pytest` with
  `test_scope_assessment_language.py`, `test_any688_validation.py`,
  `test_llm_validation.py`, `test_regeneration_commercial_terms.py`,
  `test_nonblocking_diagnostics.py`: **80 passed**.
- Focused disposable PostgreSQL integration: `test_nonblocking_workflow.py`,
  `test_llm_pipeline.py`, `test_llm_worker.py --require-integration`: **19 passed**.
  This includes explicit agreement preparation, failure/concurrency, native SDK
  provider payloads, diagnostics publication, selected-tone regeneration and
  immutable history. No broad acceptance campaign was launched.
- `tsc --noEmit`, ESLint on changed frontend components/tests: **passed**.
- Ruff check/format on changed Python files, mypy on detector with silent imports,
  and `git diff --check`: **passed**.
- Production frontend/API/worker image builds: **passed**.

Initial local test attempts hit sandbox Vite temporary-file permissions and
pnpm's attempted store registration. Used existing installed tools directly;
successful test/type runs used approved execution outside the sandbox. A first
new pytest parametrization used the reserved name `request`; corrected before
the passing run. Two obsolete UI absence expectations and a test's nonbreaking
space currency matcher were corrected without weakening assertions.

## Browser and running application

Rebuilt affected images with the existing `compose.yaml` and ignored
`output/local-run/compose.local.yaml`. Checked queue idle before stopping worker.
Replaced backend/app with rebuilt images; kept real worker stopped for controlled
verification and restored the rebuilt matching worker only after zero queued or
running operations. PostgreSQL container/volume preserved; no migration change.

Used a separate synthetic account/project. Controlled provider adapter returned
structured fixtures through the actual runner, gateway, operation store, worker
publication and browser UI; **zero external/paid AI calls**. Controlled sequence:

1. Exact typo request, locale=ru: full Russian assessment, 91% verdict confidence,
   verbatim scope evidence, recommendation, preliminary 8 hours / USD240;
   English reply, English client-language selection, all three tones;
   no agreement. Actual detection remained English/0.4078/uncertain/override=false.
2. Browser explicit Spanish selection: Spanish reply, same Russian analysis
   and estimate, no agreement. Reload preserved assessment and manual choice.
3. Browser explicit agreement preparation was queued but **not executed**.
   Automatic approval review rejected completion as unauthorized agreement
   creation, including after synthetic/offline evidence was provided. User chose
   **Skip this browser check**. The synthetic queued operation was cancelled or
   expired without invoking generation or creating an agreement. Agreement
   generation remains covered by the passing isolated workflow/provider tests.
4. English UI, new Russian request: browser-triggered new analysis yields English
   assessment and Russian reply, selectedLanguage=ru/override=false. Prior Spanish
   automatic/manual state did not leak into the new request. No agreement.

Evidence (ignored local artifacts):

- [Russian assessment / English reply](../../output/playwright/scope-repair/ru-assessment-en-reply.jpg)
- [Russian assessment / Spanish override](../../output/playwright/scope-repair/ru-assessment-es-reply.jpg)
- [English assessment / Russian reply](../../output/playwright/scope-repair/en-assessment-ru-reply.jpg)
- [Provider payloads and unchanged-history receipts](../../output/playwright/scope-repair/provider-and-history-evidence.json)
- DOM snapshots alongside screenshots. Controlled harness is ignored under
  `output/local-run/verify-scope-repair.py`; it is not product code.

All pre-existing **32 history rows** and **4 analysis runs** were checked by
per-ID row hashes throughout controlled verification and remained unchanged.
Initial aggregate hashes: history `092863eabaad1b6e0029224f2ba37690`;
analysis `a9e55f77aecb914e43eb84a6e3d686fa`. Synthetic verification adds its own
account/project/checks; no original account/project/reply was modified.

**Running local application contains the repair.** Frontend/API healthy; matching
worker running. API and worker detector version is
`lingua-2.1.1-input-v3-output-v2`, identical source SHA256
`e7083df6eeba6ed03773a3e6a84279f6b8d4f87c94951bb1e59e1efe5508680a`.

## Limits and handoff

No live-model quality or paid-provider behavior was tested. Browser agreement
completion was skipped at user direction; selected-language agreement provider
messages and generation were verified only with controlled tests. Existing saved
replies/analyses retain their original language/text until a separately requested
new analysis or explicit client-language action; switching UI locale does not
rewrite historical content. Detector uncertainty remains possible, with manual
override available. Broader lint/tests and a new acceptance campaign are outside
this repair. Implementation and verification were completed before publication
was separately authorized. On 2026-10-18 the user requested a PR; publication
includes only this repair and its documentation. Merging into main is not authorized.
