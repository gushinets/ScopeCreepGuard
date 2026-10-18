# Bounded acceptance of origin/main — 18 October 2026

**The core journey completes, but regenerated replies are not ready for acceptance with manual commercial terms.** All **20/20** live user operations completed on their first submissions. Four planned regenerations published obsolete commercial prose. No product code, prompts, validators, migrations or product expectations were changed.

Evidence: [`output/e2e/20261018-main-20-d3544de/`](../../output/e2e/20261018-main-20-d3544de/). The [plan](plans/2026-10-18-any-543-635-553-554-548-main-20-operations-acceptance.md) preceded runtime execution. This is one bounded campaign, not exhaustive acceptance.

## Frozen baseline and runtime

- Existing checkout switched to local `main`, then updated **fast-forward only** to fetched `origin/main`: **`d3544de711171619d901241ca0e763da0702f4cb`**. HEAD and the fetched remote ref remained equal throughout. No reset, stash, worktree, divergent merge, commit, push, deployment or Linear write.
- Initial tracked tree was clean. Six pre-existing untracked documents, ignored journals and local environment were preserved. The former feature branch has four SHA-distinct commits outside main's ancestry, but its complete tree equals main: its implementation is present on origin/main. The local design document is an untracked requirements source, not an application override.
- Source verification covered **691 tracked files**, with no changed bytes; nine preserved local files were unchanged at the pre-journal checkpoint. [Baseline](../../output/e2e/20261018-main-20-d3544de/baseline.json), [recheck](../../output/e2e/20261018-main-20-d3544de/source-recheck.json).
- Frontend: Next.js **16.3.0**, production build **`Sfw-fK5pP_Tsh776jnxKz`**. A retained production artifact was reused after verifying 191 frontend files against main; differences were one test file and missing `.env.example`, neither application code. A fresh build first failed Google Fonts resolution; its offline-font attempt was stopped after prolonged compilation. Production assets were checked before paid dispatch. This is source-matched artifact acceptance, not a claim of a fresh successful main build or a deployment. [Build provenance](../../output/e2e/20261018-main-20-d3544de/frontend-build-provenance.json).
- API package **0.1.0**, backend **0.1.0** and both existing worker entrypoints ran from the frozen SHA. Python **3.12.10**, OpenAI **2.43.0**, LiteLLM **1.89.3**, Pydantic **2.13.4**, SQLAlchemy **2.0.54**, psycopg **3.3.6**, ReportLab **4.5.1**. PostgreSQL **17.11** was disposable and owned by this run.
- Discovered/applied head: **`0007_nonblocking_llm`**, only on disposable PostgreSQL. Effective process overrides: `workflow_v2=true`, `llm_workflow=true`, prompt `workflow-v7-nonblocking`, diagnostics `diagnostics-v1`, requested model **`gpt-6-luna`**, matching synthetic authentication and exact Origins `127.0.0.1:13184` / `localhost:13184`. API/storage ports **18184/19184**. Existing local defaults were not assumed to enable these features; no environment file was changed. Export storage was private loopback Moto S3, not production S3. [Configuration](../../output/e2e/20261018-main-20-d3544de/effective-runtime.json), [versions](../../output/e2e/20261018-main-20-d3544de/versions.json).

Current main contains the approved independent main publication, explicit agreement preparation, nonblocking diagnostics, separate execution lanes and free-work projection. No required implementation was silently imported from another branch.

## Twenty-operation record

**Completion** below describes the user operation. Content problems do not retrospectively turn a correctly completed nonblocking operation into a transport/persistence failure. Slots were accounting identifiers, not chronological order. A failure would have consumed its slot; none was retried or replaced with seeded data.

| Slot | Operation / fixture | Completion | Content assessment |
|---:|---|---|---|
|1|RU UI × RU; unused threshold/format revision|PASS|Included; RU replies|
|2|RU UI × original EN Yoga request|PASS|Included; EN replies; reviewer concern about broad invitation for notes|
|3|RU UI × ES; separate Yoga booking page|PASS|Excluded; ES replies; internal abbreviated citation finding|
|4|EN UI × RU Arrow/email, URL and technical names|PASS|Excluded; RU replies; names/email retained|
|5|EN UI × exact original EN Arrow/email request|PASS|Excluded; EN replies|
|6|EN UI × ES MXN ambiguity|PASS|Borderline; clarification, no unconditional inclusion|
|7|Exact slot 3 input, same project, new key; preselected before dispatch|PASS|Excluded; ES replies; second automatic History entry; same citation finding|
|8|New RU complaint after ES override and recovery|PASS|Included; fresh automatic RU, `override=false`; no agreement|
|9|Explicit agreement on slot 4|PASS|RU; main result retained during processing|
|10|Explicit agreement on translated slot 5|PASS|ES; main result retained|
|11|Warm regeneration|PASS|**FAIL CQ1:** obsolete 3.5h / 30USD per hour|
|12|Neutral regeneration|PASS|**FAIL CQ1:** obsolete 3.5h / 30USD per hour|
|13|Firm regeneration|PASS|**FAIL CQ1:** obsolete 3.5h / 105USD|
|14|Historical Firm after current scope changed to include Arrow/email|PASS|Historical exclusion preserved; **FAIL CQ1:** obsolete 3.5h / 105USD|
|15|Replies-only EN→ES before agreement|PASS|No agreement created; analysis unchanged|
|16|Saved manual agreement/reply ES→EN|PASS|Manual prose translated; 2.5h / 175.35USD preserved|
|17|EN→ES return translation|PASS|Working-day/approval meaning and structured terms preserved|
|18|First refresh after project becomes 80EUR/hour|PASS|Manual amount/currency, effort and schedule retained|
|19|Refresh with unchanged inputs, new key|PASS|Same preservation and current provenance|
|20|Third refresh with unchanged inputs, new key|PASS|Same preservation; no immediate stale estimate|

Slots 19–20 used the normal API: the UI correctly removed Update estimate after slot 18. Other live submissions used the in-app browser. Agreement slot 9 was selected from the successful RU result before agreement dispatch so the two preparations covered different client languages. Slot 8 ran last to preserve the historical predecessor needed by slot 14. These choices did not change scope oracles or add slots.

All 24 main reply texts were read in full, as were regeneration and translation texts. Eight scope outcomes matched explicit pre-dispatch terms. Main results auto-saved History without Save/Create draft. Main UI inspection found no removed explanation, citation, project-context or diagnostic blocks. Agreement generation did not occur before its explicit action. All four regenerations changed only the selected tone and preserved analysis, other replies and agreement.

## Confirmed content findings

**CQ1 — regenerated prose contradicts accepted manual terms.** Reproduction sequence on this SHA/model: original Arrow/email check → explicit agreement → edit **2.5 hours / 175.35 USD / three working days after approval** → change project to **80 EUR/hour** and refresh → regenerate a selected tone. Warm/Neutral proposed 3.5 hours at 30 USD/hour; Firm and historical Firm explicitly proposed 105 USD. The saved agreement remained 2.5h/175.35USD. This occurred in all four planned regenerations, including historical scope, without extra retries. It violates manual-term authority even though nonblocking publication and persistence behave correctly. No dependent slot was blocked. [Full before/after prose](../../output/e2e/20261018-main-20-d3544de/regeneration-quality-findings.json).

**CQ2 — internal citations are not fully verbatim.** Slots 3 and 7 stored `Additional standalone pages ... are excluded.` with inserted ellipsis. Scope classification is correct, but the string is not an exact excerpt. The main UI does not display these citations. [Content review](../../output/e2e/20261018-main-20-d3544de/content-quality-review.json).

Diagnostics recorded **59 observations: 45 pass, 14 finding, zero diagnostic errors**. These are field observations, not 14 failed operations. One cosmetic-reply concern and a broad Yoga invitation remain reviewer judgments. A language finding on actual Russian suggestion prose is not independently confirmed. AI estimate proposals differing from manual prices are not themselves corruption: the editor preserved manual values and distinguished them from proposals. Translation faithfully retained older warm/firm source figures while translating the manually edited neutral reply; that pre-existing inconsistency is not a failed numerical translation. No diagnostic judgment was treated as unquestionable truth.

## Clipboard, PDF, restoration and isolation

Through actual UI controls, paid **200 EUR** and dedicated rationale **“2.5 hours × 80 EUR = 200 EUR.”** appeared in preview/actual clipboard. Free selection removed the dedicated payable fields and rationale from the effective document, retained effort/schedule, and preserved an unrelated note containing `200` and `EUR`. Saved editor values remained intact.

History → Archive current document edits → View archived check → Finalize Change Order → Prepare durable PDF → **actual browser download event** produced [free-browser.pdf](../../output/e2e/20261018-main-20-d3544de/free-browser.pdf). Its only page was rendered and visually inspected: readable layout, Spanish glyphs intact, free fee, 2.50 hours and schedule retained; no dedicated paid rationale. [Rendered page](../../output/e2e/20261018-main-20-d3544de/free-browser-page-1.png), [actual clipboard](../../output/e2e/20261018-main-20-d3544de/free-clipboard.txt), [inspection](../../output/e2e/20261018-main-20-d3544de/pdf-visual-inspection.json).

Reload restored the free flag. Unchecking restored paid preview and clipboard **exactly**, without generation. Reopening/downloading the existing free artifact after paid restoration returned identical bytes: SHA256 **`04f22ac5214439ee5cd6acfc456bc20664f6fb1e1a07ec0caeb4c0ad2561d16b`**. Both previously archived snapshots stayed unchanged; reading History/agreements left the latest working draft unchanged. [Replay/immutability](../../output/e2e/20261018-main-20-d3544de/replay-immutability.json).

Six verified same-key replays across a main check and both agreements returned their exact stored HTTP 200 results. Changed payload under the original key returned **409**. Operation rows and provider calls did not increase. The initial evidence reader incorrectly expected pending HTTP 202 for a committed replay; it was corrected against the existing API contract, without changing the logical-result expectation or product.

Slot 14's tab closed at **00:34:17.881 Moscow**, after admission and before completion at **00:34:25.012**. A new in-app tab at the unused `localhost` origin required real login and restored Spanish selection and the completed reply, without copied storage. Slot 8 subsequently reset the old override to automatic RU. With explicit permission for two supplemental non-AI checks, an isolated Chromium context started with zero cookies and zero localStorage entries, logged in through the UI and restored the saved Russian language and reply from another campaign result. No storage state was copied. [Clean-context and cancellation evidence](../../output/e2e/20261018-main-20-d3544de/external-nonai.json).

Another synthetic account and anonymous clients were denied across **17 positively verified owner routes**, including projects, drafts/revisions, analyses, operations, History, agreements, export metadata and download. Foreign responses were **404**, anonymous **401**; denied PUT did not modify the owner draft. [Isolation evidence](../../output/e2e/20261018-main-20-d3544de/security.json).

## Controlled regression set and accounting

Only the requested focused categories were exercised, with controlled providers/disposable resources and **zero external controlled calls**:

1. Production `apps/worker/main.py` scheduler: held diagnostic → user admitted → user succeeded **before diagnostic release**. Existing exact `[reject]` composition test passed.
2. Canonical free-work projection fixture: **9 Python + 9 TypeScript cases passed**, including paid/free/paid and unrelated prose.
3. Existing exact `[False-malformed]` nonblocking integration test passed: reviewer errors do not fail completed main publication; its related agreement/persistence assertions also passed.
4. Native malformed-generator JSON probe: **three structural attempts genuinely failed**; saved reply/agreement/history remained intact. Controlled probe used two baseline generator calls plus three malformed calls. [Probe](../../output/e2e/20261018-main-20-d3544de/controlled-generator.json).

No prior adversarial matrix or full suite was rerun. Initial sandbox Docker/temp-file denials and harness import/working-directory errors were resolved at the harness boundary and retained as preparation evidence, not product failures. [Focused integration log](../../output/e2e/20261018-main-20-d3544de/controlled-authorized.log), [TS parity](../../output/e2e/20261018-main-20-d3544de/ts-parity-authorized.log).

Fresh authorization in this chat was **20 user submissions / 80 total provider calls / USD1 conservative accounted cost / 90 minutes from first paid send**, earliest limit wins. A new persistent SQLite guard covered API, LLM worker, retries and diagnostics; no historical authorization or ledger was reused. All diagnostics drained, then dispatch was closed and its effective count ceiling tightened to the final count.

| Family | Completed / submitted | Physical calls | Admission→finish seconds, min / median / max |
|---|---:|---:|---|
|Main|8/8|16|7.33 / 12.05 / 17.50|
|Agreement|2/2|2|5.56 / 6.52 / 7.48|
|Regenerate|4/4|4|5.65 / 6.70 / 10.77|
|Translate|3/3|5|5.38 / 5.69 / 6.73|
|Estimate|3/3|3|3.99 / 4.50 / 5.75|
|Diagnostics|20/20 background jobs|22|4.28 / 5.87 / 17.76|

**52 physical calls = 30 generation + 22 diagnostics**, all requested/returned **gpt-6-luna**; **zero transport retries, zero structural corrections, zero unknown-usage sends**. Dispatch window **00:16:07.758–00:35:32.526 Moscow, 18 October**. Usage: **93,606 input / 22,008 output** tokens; **21,051 cached** and **16,141 reasoning** are subsets. Configured reservation rates of USD0.0000003/input and USD0.000001/output yield **USD0.0500898** accounted cost. This is configured conservative accounting, not a verified invoice; actual billed cost is unknown. Database and transport ledgers reconcile exactly. [Statistics](../../output/e2e/20261018-main-20-d3544de/statistics.json), [physical accounting](../../output/e2e/20261018-main-20-d3544de/provider-accounting.json).

## Mikhail findings and policy differences

All five current Linear descriptions and returned comment pages were read; latest relevant Mikhail Gushinets comments were **15 October**. Retained original ZIPs were rehashed and matched those comments' published hashes. Original Arrow/email and Yoga inputs were included; source contracts are retained QA reconstructions, not unavailable original customer contracts. Historical campaigns were not rerun.

| Original finding | Current bounded evidence |
|---|---|
|D01 CO/short-label gate — ANY-543/635/554|8 main results publish without CO; 2 explicit agreements succeed. Combined readiness gate intentionally removed.|
|D02 mixed language — ANY-543/635|Actual prose in the new language matrix matches selection. Historical mixed candidates were inspected, not broadly replayed. Invalid content is diagnostic under current policy.|
|D03 scope reversal / historical context — ANY-553|8 scope oracles match; historical regeneration preserves S0 after S1 change. CQ1 commercial prose still fails.|
|D04 manual USD→EUR corruption — ANY-554|All 3 refreshes retain 175.35USD, effort/schedule and current 80EUR provenance.|
|D05 ordinary History loss — ANY-548|Every new main result auto-saves History before agreement; reload/recovery demonstrated. Legacy disabled workflow not certified.|
|D06 unapproved dates / working→calendar days|No unconditional new delivery date confirmed in main replies; manual round-trip preserves working-day/approval meaning. Original adversarial deadline matrix not rerun.|
|D07 cosmetic novelty — ANY-553|All four selected texts differ; one reviewer cosmetic concern remains. No claim of proven semantic novelty in every variant.|
|D08 missing-data explanation — ANY-554|Incomplete agreement identifies missing parties in editor/preview. No additional empty-document/PDF campaign.|
|D09 translation preservation — ANY-635|Three planned translations complete, including edited ES→EN→ES; exact historical parser corpus not rerun.|
|Reviewer format/outage and scheduling|Focused controlled malformed-reviewer and production-lane checks pass.|

Older Linear criteria explicitly require invalid language/scope/novelty/terms content to be rejected or repaired. **Diagnostic-only publication does not satisfy those rejection criteria.** Current design deliberately permits publication with findings; genuine malformed generator JSON still fails. Manual commercial authority remains required and CQ1 is not excused by nonblocking policy. No Linear status or criterion was changed to reconcile that difference.

## Remaining coverage and cleanup

The sample does not establish a failure frequency, exhaustive multilingual correctness, deployment/default-flag readiness, production S3 behavior, broad adversarial robustness or full-suite health. Synthetic project date entry settled on **2026-12-10**, captured in frozen inputs; no calendar-date deadline assertion depends on it. The isolated production artifact uses offline font CSS. Live agreement failure was not induced; the focused controlled test covers preservation after failure.

The in-app tool did not expose a dismissible replacement dialog and the reserved Warm operation dispatched, consuming slot 11 once. After the user authorized the pending external-browser request, two supplemental checks used a restored backup of the **actual completed campaign database**, with paid dispatch closed. An empty browser context restored saved data after real login. Dismissing the real manual-replacement confirmation preserved the saved manual edit and sent **zero regeneration requests**. The original text was restored through the UI; operation inventories and the 52-call ledger were unchanged. This was supplemental verification of existing results, not another AI campaign or a seeded replacement journey.

Cleanup completed: owned campaign and supplemental processes stopped, their labelled disposable PostgreSQL containers removed, test ports no longer listening, and the private connection file removed. The private synthetic database backup is retained outside sanitized evidence; it includes synthetic authentication data and is not for sharing. Generated build/dependency copies and evidence remain ignored on disk for reproducibility. Unrelated resources, original retained fixtures and local work were preserved. All 691 tracked file hashes and the nine pre-existing local-file hashes remained unchanged. AGENT.md and WORKLOG.md remain ignored; the latter has a clearly labelled acceptance-work entry appended after preservation verification, with no invented human or billable hours. [Supplemental cleanup receipt](../../output/e2e/20261018-main-20-d3544de/supplemental-resource-cleanup.json), [final preservation check](../../output/e2e/20261018-main-20-d3544de/final-source-recheck.json), [evidence index](../../output/e2e/20261018-main-20-d3544de/README.md).

1. **Does the tested core journey work on origin/main?** Yes for operation completion, independent main/agreement publication, translation, manual estimate preservation, Copy/PDF and persistence; client-ready regeneration is not fully acceptable.
2. **What reproducible product failures remain?** Regeneration repeatedly proposes obsolete commercial terms despite the saved manual agreement (CQ1; four planned cases).
3. **What content-quality findings remain?** CQ1, internal abbreviated citations in two Yoga results, and a reviewer-only cosmetic/broad-invitation concern requiring human judgment.
4. **What can be submitted for human acceptance?** The frozen 20-operation evidence, successful core/material/export/persistence/isolation paths, and the confirmed failures/coverage limits. Do not submit regeneration commercial prose or the whole product as unconditionally accepted.
