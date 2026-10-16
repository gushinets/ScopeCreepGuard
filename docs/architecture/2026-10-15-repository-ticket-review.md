# Scope Creep Guard: repository and ticket review

Reviewed on 15 October 2026 (Europe/Moscow).

**Conclusion: the six open tickets are not all ready for acceptance.** The latest code contains substantial fixes, but the default application path still reproduces several earlier failures. The explicitly enabled LLM workflow fixes persistence and historical-context handling, while its validation still accepts some outputs that violate the tickets.

## Reviewed version and scope

- GitHub repository: [gushinets/ScopeCreepGuard](https://github.com/gushinets/ScopeCreepGuard).
- Remote main: [f00e1014c376cba9e5dc65e73421a98c3aa3c37e](https://github.com/gushinets/ScopeCreepGuard/commit/f00e1014c376cba9e5dc65e73421a98c3aa3c37e).
- Local branch: codex/any-663-llm-workflow at 4450eca. Its committed Git tree is identical to remote main: b98addef87889fa5fc02f4ec9d6249e49e74a3f5.
- Read all seven issue descriptions and their discussion threads, including the linked 11 October acceptance comments and subsequent product decisions.
- Reviewed frontend state and editing flows, generation, language detection/validation, project persistence, history, document preparation, ownership boundaries, migrations, worker publication/recovery, and deployment activation.
- Existing .gitignore edits and the two untracked design documents were preserved. No application code, ticket, production data, or deployment was changed.

This review combines source inspection, the existing automated suites, direct API reproductions against disposable PostgreSQL, and controlled provider-output probes. It is not a new live-model acceptance run. Frequencies from the 8/11 October ticket comments are historical evidence, not measured rates for this commit. Attached screenshots/videos/ZIPs were not independently re-inspected.

## Runtime modes matter

[Settings defaults](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/core/config.py#L25) leave both workflow_v2 and llm_workflow false. The frontend [selects its provider](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/app/page.tsx#L4) using SCOPE_GUARD_WORKFLOW_V2. The default Compose stack does not explicitly enable either workflow, although operators can supply configuration.

| Mode | Project email/end date | Completed checks | Generation validation |
| --- | --- | --- | --- |
| Default compatible mode | Browser storage; absent from project API | Explicit Create draft required for full history | Provider shape and language tags; no actual-language correction loop |
| Persistent workflow only | Stored server-side | Working result persists; History publication remains explicit | Earlier direct generation path |
| Persistent + LLM workflow | Stored server-side | Worker automatically publishes completed checks to History | Staged validation and bounded correction; remaining gaps below |

The final mode requires coordinated frontend/API activation, the migration to 0005_llm_workflow, a running LLM worker, and provider-budget configuration. Merely merging the implementation does not activate it. Deployment activation was not performed or verified against a live application.

## Prioritized findings

### F1 — P1: the new scope validator accepts a reversal of the saved verdict

**Tickets:** ANY-553; also relevant to client-facing replies and Change Orders.

With frozen scope “Arrow and email alerts are excluded” and accepted verdict out_of_scope, the actual ReplyStage validator accepted:

> Of course, we can add Arrow and email alerts under the existing agreement at no extra cost. Send the recipient list and we will get started.

The separate scopePosition field remained out_of_scope. The [text check](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/stages.py#L244) rejects a finite set of phrases, which does not cover this formulation. The [metadata equality check](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/stages.py#L292) cannot establish that the actual message preserves the position. Because validation succeeds, this candidate does not trigger correction.

**Impact:** enabling the new workflow does not reliably prevent the dangerous “excluded work is already free” failure identified in the ticket.

**Correction:** validate the actual message's scope and payment commitments against the frozen analysis. Cover paraphrases and all verdicts; adding this phrase to a denylist alone would leave the same class of gap.

### F2 — P1: default-mode regeneration still uses today's scope for a historical result

**Ticket:** ANY-553.

Direct API reproduction:

1. Analyze and explicitly save a draft whose scope excludes Arrow/email.
2. Update the project's current scope to include them.
3. Regenerate the saved request.
4. The call succeeds with HTTP 200, but the generator receives the new scope; the saved draft still contains the excluded-work scope.

[GenerationUseCases.regenerate_reply](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/services/analysis/use_cases.py#L132) loads the current project. The default client request also omits a historical selector.

**Correction:** bind regeneration to owned persisted historical context or its verified proof, including the accepted verdict. The enabled LLM workflow already freezes the historical run; its coverage passed, but F1 still applies there.

### F3 — P1: language checks still accept incorrect or mixed-language text

**Tickets:** ANY-543 and ANY-635; regeneration also affects ANY-553.

Two independent reproductions:

- **Default mode:** a controlled OpenAI response with clientLanguage=en and all three replies in Russian is accepted after one provider call. The [adapter](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/openai.py#L161) parses structure/tags rather than verifying the actual language.
- **New workflow:** an otherwise English reply ending with “Сроки согласуем отдельно.” passes validate_stage. The [detector](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/detection.py#L40) requires only 75% language dominance, allowing a genuine foreign-language sentence. Its reported whole-text confidence was 1.0 for this controlled example.

**Correction:** distinguish request-language selection from output-language enforcement. After exempting legitimate names and verbatim quotations, reject clearly foreign prose spans and feed those failures into bounded correction. Ensure every supported runtime uses that enforcement.

### F4 — P1: ordinary results still do not enter History in the default mode

**Ticket:** ANY-548.

A direct POST /api/analyze returned HTTP 200. A subsequent GET of that project returned history: []. No draft creation was performed.

The [analysis service](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/services/analysis/use_cases.py#L85) returns a result and proof without persisting it; the [default frontend](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/components/scope-guard/store.tsx#L590) keeps it in React state until explicit draft creation.

**Impact:** the original “successful analysis disappears after reload unless Create draft is clicked” acceptance gap remains in the default configuration.

**Correction:** complete and verify the coordinated rollout of automatic publication, or provide equivalent persistence in the supported default mode. The new worker's automatic History publication, including a result that cannot overwrite a newer request, passed deterministic integration coverage.

### F5 — P2: project email and end date remain browser-only in the default mode

**Ticket:** ANY-547.

A direct project-create/read reproduction submitted clientEmail=client@example.test and endDate=2026-12-01; neither field was present in the returned project. The report's evidence represents missing keys as null.

The [project form](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/components/scope-guard/new-project-view.tsx#L96) submits these fields only with the persistent workflow. Default edits [write browser storage](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/components/scope-guard/store.tsx#L399), and the compatible project DTO/persistence does not store them.

**Correction:** persist and read both fields through the supported server path. The v2 implementation already does this; verify its activation rather than treating the existing code as proof of rollout.

The later ticket comment explicitly accepts having Edit/Delete only on Projects. Their absence on Scope check is not a finding.

### F6 — P2: Change Orders still do not explain which required data is missing

**Ticket:** ANY-554.

The shared [preview/copy document builder](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/lib/change-order/document.ts#L100) omits empty parties and commercial rows and leaves work/schedule sections blank. [Copy and default PDF download](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/frontend/components/scope-guard/change-order.tsx#L100) have no missing-data warning. PDF preparation adds dashes for empty effort/fee, but that does not explain missing parties, description, or schedule.

The new finalization validator rejects an empty description or invalid paid amount/currency. However, it does not require parties or schedule, and the shared editor/copy still lacks guidance. Thus the new path adds some protection without satisfying the complete missing-data criterion.

**Correction:** identify missing required fields in preview/copy/PDF or present an understandable warning before export. Keep optional email and approval date optional, as clarified in the ticket. Blocking export is not itself required.

### F7 — P2: regeneration checks do not enforce meaningful novelty

**Ticket:** ANY-553.

The default adapter accepted exactly the previous reply after one provider call. The new validator rejects only [whitespace-normalized equality](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/stages.py#L297). Appending only “Thank you.” to the old message passed validation.

**Correction:** reject cosmetic-only changes and request a meaningfully different formulation while preserving facts and scope. Keep human evaluation for subjective writing quality; this concrete suffix-only example does not require judging tone quality.

### F8 — P2: unsupported deadline promises can pass the new validator

**Ticket relevance:** ANY-553 and ANY-554.

With no such deadline in the frozen facts, the validator accepted:

> These additions are outside the agreed scope and require approval. We will deliver everything next week. Please confirm the recipient list.

The [timeline check](https://github.com/gushinets/ScopeCreepGuard/blob/f00e1014c376cba9e5dc65e73421a98c3aa3c37e/backend/src/scope_guard/integrations/llm/stages.py#L255) only recognizes tomorrow/mañana/завтра. A relative promise such as “next week” has no numeric token and bypasses both this check and numerical-term checks.

**Correction:** validate explicit and relative schedule commitments against saved/proposed terms, including localized formulations. Reject unsupported commitments instead of relying on three keywords.

## Ticket disposition

These are review recommendations, not Linear status changes.

| Ticket | Linear state | Assessment at reviewed commit |
| --- | --- | --- |
| [ANY-543 — client language](https://linear.app/paveldik/issue/ANY-543#comment-dc4b6146-aaa1-4cbf-aad5-b67946be7acf) | In Progress | Keep open. New staged correction is present, but default enforcement and mixed-language rejection remain incomplete (F3). |
| [ANY-544 — independent replies](https://linear.app/paveldik/issue/ANY-544#comment-27923514-74a0-4dd4-9d8b-1e14cd71ef94) | Done | Respect the later acceptance decision. Language was explicitly assigned to ANY-543. No new live tone-quality acceptance claim is made here. |
| [ANY-547 — editing/deletion](https://linear.app/paveldik/issue/ANY-547#comment-39c6f533-706b-4fd0-a281-cf4caf3c00c0) | In Progress | Remaining accepted scope is email/end-date persistence. Implemented in v2, unresolved in default mode (F5). |
| [ANY-548 — persistence/history](https://linear.app/paveldik/issue/ANY-548#comment-d05aefbc-3368-4374-bfb6-28f870ff8257) | In Progress | Automatic publication passes in the new LLM workflow; default mode still requires Create draft (F4). Verify target deployment before closure. |
| [ANY-553 — regeneration](https://linear.app/paveldik/issue/ANY-553#comment-ebe96fa1-2667-48b0-a5a3-9fb371f300e8) | In Progress | Keep open. Historical context is fixed in the new path, but F1/F3/F7/F8 remain; default mode also has F2. |
| [ANY-554 — Change Order](https://linear.app/paveldik/issue/ANY-554#comment-753b6fff-79ad-4c8c-bb06-6c413dec4602) | In Progress | Keep open for the explicitly requested missing-data guidance (F6). F8 is an additional commitment-validation gap. |
| [ANY-635 — Spanish](https://linear.app/paveldik/issue/ANY-635#comment-bb85715f-0d84-4dc0-b088-846057f114f0) | In Progress | Understandable language dropdown is fixed. Server-side selection/translation is implemented in the new workflow; full output-language enforcement still has F3. |

All seven issues have the Scope Creep Guard project and empty labels. Under the repository's AnyToolAI ticket-audit skill, they lack the required single type: and func: labels. Suggested classification for the original feature deliverables is type:feature + func:dev; confirm whether reopened fixes should instead be classified type:bug. No labels were changed.

## Verification results

| Check | Result |
| --- | --- |
| Frontend Vitest | 334 passed across 47 files |
| Backend unit/API/architecture | 473 passed |
| Backend database integration | 71 passed |
| Compose startup/migration/restart and entrypoint signals | 3 passed |
| Frontend production build | Passed |
| Frontend TypeScript, including after build | Passed |
| Frontend lint | No errors; one existing unused-variable warning in lib/llm/schema.test.ts |
| Backend Ruff lint/format | Passed; 308 files formatted |
| Backend mypy | Passed for 197 source files |
| Generated frontend API contract freshness | Passed |
| Frontend container-entrypoint tests | 3 passed |
| Controlled regression probes | Confirmed F1–F5, F7 and F8 as described; F6 confirmed by source inspection |

Initial frontend execution had four 5-second timeouts. Rerunning with two workers and a 30-second test timeout passed all 334 tests. Initial Python checks used a stale nested environment, then encountered an inaccessible system temporary directory. Using the root workspace environment and test-owned workspace temporary folders resolved these setup failures. They are not reported as product defects.

Passing suites do not demonstrate acceptance of outputs they do not reject. For example, some tests intentionally use identical reply fixtures to exercise plumbing; the adversarial scope/novelty/language probes above expose separate requirement gaps.

## Evidence and limits

Review-only reproduction artifacts are stored locally under output/review-2026-10-15/:

- validator-probes.py and validator-probes.json: actual legacy adapter and new stage-validator behavior with synthetic provider output.
- default-api-probes.py and default-api-probes.json: project field loss, ordinary-history omission, and historical regeneration using current scope through the real API and disposable PostgreSQL.

Run validator probes with the root workspace Python environment. Run API probes from backend/ because the migration helper requires that working directory. Both scripts use synthetic inputs; API probes create and remove their own labeled PostgreSQL container/database.

No real provider calls were made. This review therefore does not establish live RU/EN/ES success rates, final tone quality, or production rollout state. Existing automated PDF checks passed, but no new visual inspection of every PDF page or manual browser acceptance run was performed. The connected GitHub combined-status response contained no statuses and is not treated as evidence of green remote CI.
