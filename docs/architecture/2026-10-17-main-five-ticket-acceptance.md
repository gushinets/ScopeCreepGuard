# Current-main acceptance: ANY-543 / 635 / 553 / 554 / 548

17 October 2026, Europe/Moscow. **Overall acceptance: FAIL.** Planning was followed by execution. A bounded English original journey completed through editing, actual Copy/PDF and clean-context restoration. The requested multilingual/regeneration workflow did not pass. Dependent repetitions stopped at observed gates; accepted intermediate stages were not counted as full checks.

No product logic, prompts, validators, migrations, acceptance expectations, tracked environment files, Linear writes or Git publication changed. Local acceptance does not establish production rollout.

## 1. Frozen baseline and runtime

- Fetched origin, switched to main, fast-forward only: already current.
- HEAD and fetched origin/main: **29c67f4580bea8a7d58530beaeea2abb537af1a9**. Remote main was also observed unchanged during testing. No midway source update.
- Tracked files were initially clean. The complete tracked-file hash inventory in `baseline.json` still matches. Both unrelated `docs/design/project-draft-ai-workflow*.md` files were preserved.
- No stash/reset/discard, worktree, divergent merge, commit, push or merge.
- Production frontend: Next.js **16.3.0**, Node **24.19.0**, build **UfsbOgFKzRz6-uScdvKBf**. Installed Next.js deployment/environment guides were read. First build compiled but worker spawn hit sandbox EPERM; the permitted rerun passed.
- API and existing LLM/export workers: same frozen source SHA; `scope-guard` and `scope-guard-api` **0.1.0**. Python **3.12.10**, FastAPI **0.143.0**, Uvicorn **0.54.0**, OpenAI **2.43.0**, LiteLLM **1.89.3**, Pydantic **2.13.4**, PydanticAI slim **2.2.0**, SQLAlchemy **2.0.54**, psycopg **3.3.6**.
- Actual prompt **workflow-v6**, schema **stage-v1**, policy **workflow-policy-v1**. Historical v3/v5 reports are different versions.
- Owned PostgreSQL **17.11**, UTF8/UTC, migrated through the guarded runner to **0006_profile_metrics**. Container image digest and server build are recorded in database-runtime-metadata.json. No application/customer database target.
- Live frontend/API/private S3 ports **13170/18170/19170**; separate controlled runtime **13171/18171/19171**. Matching API/LLM/export processes shared each runtime's own database.
- Recorded process overrides: workflow_v2/llm_workflow true; exact **gpt-6-luna**; matching synthetic auth; exact loopback Origins; private export bucket/endpoint; conservative input/output bounds **USD 0.0000003/0.000001 per token**, per-operation ceiling USD1.
- Local pre-override config was flags false, baseline migration target, model gpt-5.6-luna, configured key and missing rate bounds. It was recorded, not silently used.
- Actual S3ObjectStorage/ExportWorker used loopback Moto **5.2.4** private storage. This tests the application protocol, not external production S3.
- Chromium **156.0.8078.4**, Playwright **1.64.0**, independent contexts, real registration/login forms, clipboard and download events.

Sanitized launch/dependency/config evidence: `effective-runtime.json`, both runtime receipts and `baseline.json`. Tracked env files were unchanged.

## 2. Requirements and reviewer provenance

Read the five Linear descriptions/discussions, including all specified Mikhail Gushinets rejection IDs. Pagination was exhausted; no newer comments than 15 October were present. No Linear mutation occurred.

Later requirements govern actual text language, manual override/reset/restore, preserved conditions, automatic History and missing-data guidance. Email/approval date remain optional; no blanket incomplete-export block was invented.

All five 15 October ZIPs were retrieved and matched published SHA-256:

| Ticket | Verified SHA-256 |
|---|---|
| 543 | c14410581a3e4891329053ed55aaa9a7cd46fab69e0fe89a30a48c59d55effb0 |
| 635 | 43d7d9b8f3de12e9012a61079c8fd3d74f8f80f0e01b1479597c0fc335b82d26 |
| 553 | a35895b4a14a901b8741eebe2ae5f0104b7004a8b6f7ed949fa2fa45829be1fa |
| 554 | 7ce3beb8e8823b362644c6f0f587f60a75770dde4362283a4d8417c2ce4e8291 |
| 548 | 6e9b13811e61e1be6e2a00f0359d6b08f90881c30bcbc1142fa61d1761c1dee8 |

The existing extracted ANY-635 copy matched all 85 indexed files. Inspected README/results/matrix, actual S0/S1 inputs, D1/T1/E1 before/after, negative fixtures, operations/steps, replay instructions and relevant screenshots/PDFs. That package contains 54 matrix rows, 15 operation/review records and 44 stages. Its 14 failed live full checks remain historical failures.

Original E1 actually changes manual 175.35 USD to EUR while adding an 8×80=640 EUR rationale. Original T1 preserves manual D1 after failed translation. The exact short Spanish description was reused in controlled UI exports:
“Añadir Arrow y notificaciones por correo. ¿Confirmáis el cambio? ¡Gracias! Acción, revisión y coordinación.”

S0/request copies are exact reviewed QA fixtures, themselves labeled synthetic/reconstructed; they are not asserted to be original customer contracts. Yoga scope/request came from Mikhail's 11 October discussion. New long/glyph/mixed/race fixtures are synthetic. Older 8/11 October multimedia packages were not exhaustively downloaded again.

Read the 15 October repository review, 16 October acceptance verification, current profile/metrics/follow-up verification, ownership/workflow/runtime instructions and plan README. Historical results were not current passes.

## 3. Real-provider campaign A

All requested/returned paid models were **gpt-6-luna**. Check oracles were recorded before dispatch from the agreement.

| Case | UI/client; expected scope | Full result | Actual |
|---|---|---|---|
| M1 | RU/EN; excluded Arrow/email | PASS corrected | Completed analysis, three replies, CO and automatic server History |
| M1-R2 | Identical inputs, new key | PASS corrected | Separate result/History |
| M1-R3 | Identical inputs, new key | PASS corrected | Separate result/History |
| M4-R1 | RU/RU; excluded | FAIL | Invalid semantic decision, change_order_review_1 |
| M2-smoke | RU/ES; excluded | FAIL | Same CO review-response structure gate |
| YOGA-IN | EN/EN; colour/reordering included | FAIL | Three ordinary English CO notes falsely rejected |
| B2-smoke | EN/EN; MXN conversion unspecified | FAIL | Invalid semantic decision at CO review |

**Full-check completion 3/7; first-attempt completion 0/7; corrected completion 3/7; terminal failures 4/7.** All three publications had the accepted scope position, Russian explanations and complete English replies/CO. Observed invalid generated publications: **0/3 completed results**, not proof of universal reliability.

The requested 18-check matrix remains incomplete:

| UI × client | Executed/requested | Completed | Remaining |
|---|---:|---:|---|
| RU × EN | 3/3 | 3 corrected | Done |
| RU × RU | 1/3 | 0 | 2 BLOCKED |
| RU × ES | 1/3, independent prerequisite smoke | 0 | 2 BLOCKED |
| EN × RU | 0/3 | — | BLOCKED |
| EN × EN | 0/3 | — | BLOCKED |
| EN × ES | 0/3 | — | BLOCKED |

These five matrix attempts overlap the seven checks above; do not add them. Yoga/borderline are the additional branch smokes. Instagram topics and Spanish marketing repetitions were NOT RUN after the shared gate was confirmed.

### Material deviations

**F1 — ordinary valid English falsely rejected (543/635/554).**
M1 rejected “This change order is a draft and is not legal advice.” at EN confidence0.6632 and “This document is a draft. It is not legal advice.” at0.554. A third formulation passed. R2/R3 each needed correction; Yoga exhausted three notes, ending at0.6907.

In this specifically audited note cohort, **7/10 valid English note candidates were rejected**. This is a field-level denominator, not a rate for all valid model output. Evidence includes provider outputs0003/0004, database-smoke and YOGA-IN. Two exact ordinary-note fixtures were independently replayed twice: **4/4 failed complete controlled checks**. SQL in the second pair shows zero History. Their expected-to-succeed regressions remain failing; no validator threshold changed.

**F2 — real reviewer decisions terminate the user journey (543/635/553/554).**
The real model returns violation fields such as `candidate.labels.clientEmail` and `candidate.text`. Structured output returns, but the subsequent review-field check rejects the decision and the operation terminates with `errors.providerOutputIncomplete`, “review.structure: invalid semantic decision.”

Observed in M4-R1, M2-smoke, B2-smoke, G-warm-2 and TD1-EN-ES. The invalid review object is not published as client material; the acceptance defect is the terminated result/replacement path.

**F3 — faithful generic timeline translation rejected (543/635).**
T0 EN→ES exhausted three CO candidates at `timelineImpact.commercial_terms`. Source: “The accepted preliminary estimate is 12 additional hours. No delivery date or schedule commitment has been established.” The first two Spanish candidates retained that meaning and were rejected; the third inserted USD240.00 into that field and was correctly blocked. Do not classify all three rejections as false. Saved materials remained identical.

**F4 — post-rate-change current-edit archive blocked (554; controlled observation).**
In the separate controlled browser: change only pricing to80 EUR/hour, successfully refresh estimate, retain/edit manual terms, then Archive current document edits → **409 errors.analysisStale**. No updated hourly PDF was created. Earlier successful PDFs and a fresh glyph-only export are not counted as a repair of this journey.

### Live operation statistics

| Kind | Attempts | First success | Corrected success | Terminal failure | Physical calls | Admission-to-terminal latency |
|---|---:|---:|---:|---:|---:|---|
| Full check | 7 | 0 | 3 | 4 | 40 | 18.226–38.758s |
| Warm regeneration | 2 | 1 | 0 | 1 | 4 | 7.671–12.492s |
| Translation | 2 | 0 | 0 | 2 | 9 | 14.543–22.442s |
| Estimate refresh | 3 | 3 | 0 | 0 | 6 | 11.281–12.923s |

Latency includes queue/validation; it is neither full-browser nor pure-provider latency.

G-warm-1 changed wording and preserved analysis, CO and other tones. G-warm-2 preserved saved content on failure. Remaining warm and all neutral/firm repetitions are BLOCKED. Live historical S0 regeneration after S1 remains unverified; current native regressions cover frozen context separately.

Generic T0 and distinct short manually edited TD1 EN→ES failed. Genuine live ES→EN→ES, restoration of a successful live override and its new-complaint reset remain BLOCKED.

## 4. Requirement-to-case matrix

| Requirement/case | Status | Evidence/limit |
|---|---|---|
| Real register/login, project validation, optional blanks, reload | PASS live | A1/M1 auth/project records; HTTP201 registration; required errors before valid progression |
| Manual2.5h/175.35USD vs current80EUR/hour | PASS for3 live refreshes | First UI, next2 same authenticated API; reload. Live setup also changed scope S0→S1; historical analysis retained |
| AI suggestion/manual rationale separation | PASS observed | Manual175.35USD and effort retained; displayed rationale empty; aiValues has its own EUR binding |
| Currency-only edit | PASS live UI | EUR→RUB→USD preserves175.35 without conversion claim |
| Six missing fields individually and together | PASS live UI/Copy/reload | Parties, description, effort, fee, schedule: guidance/incomplete marker; blanks do not resurrect |
| Applicable finalization field errors | PASS actual UI/API | Incomplete archive400: description=required, additionalCost=required. Currency present; no invented party/email/date requirement |
| Optional email/approval date | PASS actual exports | Both blank |
| Live-derived edited EN Copy/PDF | PASS | Actual clipboard, real worker/S3/download, independent SQL checksum/size |
| ES D1/free/missing-party/glyph/long PDFs; RU regression | PASS controlled original browser path | Six real downloads; not substituted for live ES acceptance |
| Explicit2.5×80=200EUR post-rate document | BLOCKED at archive | Manual conditions exist; no successful hourly PDF or automatic recalculation claim |
| Desktop/390px dropdown | PASS control | Readable names, accessible label, visible keyboard focus, arrows/Enter, control fits viewport |
| Native popup clipping | NOT RUN | Headless page capture cannot establish OS popup geometry |
| Cancel manual reply replacement / translation | PASS live browser, zero calls | Manual edit kept, no operation dispatched |
| Recoverable HTTP failure preserves reply | PASS injected browser503 on live saved data | Old content retained; valid replacement after retry BLOCKED at real review gate |
| Automatic History without extra Save/Create/Complete | PASS for3 live completed checks | database-smoke shows check1/History1 before manual archiving; distinct analyses for3 keys |
| History read-only, reload, logout/clean login | PASS live | Full saved document restored; clean context localStorage length0 before login |
| Same-key replay / changed payload | PASS actual API | Same logical result, zero new calls; changed locale409 |
| Lost successful HTTP response | PASS completed-receipt replay | Browser dropped actual successful replay response; retry identical. Fresh first-commit loss not separately injected |
| New keys, identical complaint | PASS live | M1/R2/R3 distinct intentional checks |
| Account/anonymous isolation | PASS HTTP | Ten owner-confirmed routes200, B404, anonymous401; foreign Draft PUT404. Includes analysis via operation result, CO, export/download |
| Close tab during admitted processing | PASS controlled browser | Queued operation survives close/return |
| Older result / newer request | PASS controlled browser+API | Newer UI text immediately saved through owned API; old applied=false and retained in History. No second newer analysis admitted |
| Older formats/backfill/worker recovery | PASS current controlled SQL regressions | 10/10 persistent-workflow/worker tests; not live historical customer data |
| Mixed URL/email/code/names and manual fallback/reset | PASS controlled browser | Dominant ES detected; uncertain “Arrow + email” falls backEN; manualES, newRU override=false, exact oldES restored/reloaded without new scope check |
| Former legacy generation configuration | PASS safe retirement only | Current API/SQL tests: flags-off503 workflowUnavailable, persistent compatibility426, no provider/storage mutation. No successful legacy journey claimed |

**Seven actual successful downloads, 12 rendered pages:** one live-derived EN page and eleven controlled pages including six-page ES continuation. Every page visually inspected; all80 long markers occur once; no clipping/overlap, missing/duplicated content or broken glyphs observed. A dedicated actual export contains `ñ á é í ó ú ¿ ¡`. Free work removes stale175.35; missing parties are marked in Spanish.

All7 downloaded byte streams match PostgreSQL checksum/size. Every anonymous direct object GET returns403; export jobs succeeded first attempt. See independent-export-assertions, actual PDFs and rendered pages. This is not a standalone PDF helper.

## 5. Controlled campaign B

Canonical tests use unchanged native schema/SDK/gateway, worker, disposable PostgreSQL and publication, not direct validator calls.

**23 categories ×3 modes: 69/69 assertions passed.** Categories: EN+shortRU; Hola+RU; excluded-free/included-paid/borderline-certain in EN/RU/ES; punctuation/Thank-you-only; unsupported next week in three languages; unit/currency/amount/decimal mutations; working→calendar days; omitted approval dependency.

Each runs invalid→valid correction, persistent invalid→bounded failure with saved content, and valid neighbor. Results: **92 invalid generator candidates, 0 invalid publications; 23/23 preserved documents on persistent failure; 46/46 valid corrections/neighbors succeeded; 619 controlled physical calls.**

Semantic reviewer responses are controlled too. These measure enforcement/orchestration, not live reviewer accuracy.

Additional non-overlapping records:

- Two valid short English notes, two runs each: **4/4 failed full checks**,24 calls. Second pair adds independent SQL (zero History).
- Twelve initial positive scope/borderline fixtures accidentally duplicated initial wording:12 correct novelty failures,102 calls. Retained as invalid harness attempts; distinct wording reruns passed. No failed attempt erased.
- Separate browser runtime:9 controlled checks,1 translation,1 estimate,51 calls. Includes one admitted recovery setup interrupted by a queued-state harness mistake. All operations completed; the post-rate archive action still failed409.
- Mixed ES/URL/email/Make.com/SKU input passed; uncertain-language manual fallback, new-complaint reset and exact old-result language restoration passed. First same-text selector chose originalEN archive; exact-ID UI/network observation corrected it without new generation.
- Original headings and short D1 working-day translations have current native regression coverage, not proof of live D1 translation.

Instrumented controlled total: **796 physical sends**, zero external model calls/cost. Supporting repository tests have additional unmetered synthetic sends and are excluded from796.

## 6. Budget, attempts and verification

New user authorization: **400 physical calls / USD5 /3h from first paid send**, earliest limit. Historical95/96 ledger and inherited24-call authorization were not reset/reused.

One persistent SQLite guard covers API/worker processes/restarts, transactional reservation before dispatch, original wall deadline, exact model/endpoint/tier/tool checks and conservative unknown-dispatch reservation. Five free guard tests passed.

- **59 external calls**, requested/returned **gpt-6-luna**, usage returned for all.
- Includes38 generator and21 reviewer sends; semantic retry sends8, transport retries0.
- Input111,159; output25,005; cached input27,836; cache writes74,992; reasoning18,075 tokens. Reasoning is included in output.
- Conservative guard total **USD0.0583527**; Standard short-context tariff estimate **USD0.02298796**. Provider-reported dollars/invoice unavailable; these are not confirmed billing.
- Pricing inspected: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).
- First paid send **15:17:16.676929 MSK**,17 October. No budget exhausted; product blockers stopped paid repetitions.
-14 live operations:7 succeeded (4 first attempt,3 corrected),7 terminal failures. This overlaps the per-kind table.

| Supporting verification | Actual outcome |
|---|---|
| Native pipeline/acceptance journeys |10 passed,93.88s|
| Legacy/LLM API/S3 group |6 passed,35.90s|
| Persistent workflow/worker |10 passed,45.08s|
| Acceptance labels/commercial |33 passed,21.82s|
| Campaign guard |5 passed,0.36s|
| Production build |Passed permitted rerun|
| Independent export checksum/size/privacy/text |7 PDFs passed|
| Source/unrelated design preservation |Passed|

All product failures remain. Setup/tooling logs retain sandbox/network restrictions, dependency pin correction before paid calls, migration working directory, full-Chromium versus failed headless-shell download, Windows event loop, HTTP201/receipt-shape, details-open/archive-route, queued-state and same-text archive selector mistakes. They are not product passes.

Provisioning helper's generic out-of-scope caption is wrong for Yoga/B2; authoritative pre-dispatch check records use in_scope/borderline, as this report does. Expectations were not changed to turn failures green.

Automatic approval review twice blocked incomplete finalization as durable agreement creation. After disposable/incomplete read-only proof, the user explicitly authorized synthetic local finalization; the probe/exports completed. Nothing was sent to clients.

## 7. Evidence, commands, cleanup and limits

Ignored root: `output/e2e/20261017-main-29c67f4/`.

Start with statistics, effective-runtime, case-matrix, both final database snapshots, independent-export-assertions and artifact-index JSON. Browser artifacts retain actions, requests, IDs, before/after, screenshots, actual clipboard, PDFs/pages. Provider/SQL records retain candidates, validation and corrections. Verified original packages remain provenance, not a new public attachment.

Plan: [execution record](plans/2026-10-17-any-543-635-553-554-548-main-acceptance.md).

Commands actually used, from backend:

~~~text
../.venv/Scripts/python.exe -m pytest tests/integration/test_llm_pipeline.py tests/integration/test_acceptance_journey.py --require-integration -q -p no:cacheprovider
../.venv/Scripts/python.exe -m pytest tests/integration/test_generation_workflows.py tests/integration/test_llm_api.py tests/integration/test_s3_exports.py tests/api/test_supported_generation.py --require-integration -q -p no:cacheprovider
../.venv/Scripts/python.exe -m pytest tests/integration/test_persistent_workflow.py tests/integration/test_llm_worker.py --require-integration -q -p no:cacheprovider
../.venv/Scripts/python.exe -m pytest tests/unit/test_acceptance_labels_translation.py tests/unit/test_acceptance_commercial.py -q -p no:cacheprovider
~~~

From repository root, isolated tooling:

~~~text
output/e2e/20261017-main-29c67f4/venv/Scripts/python.exe output/e2e/20261017-main-29c67f4/runtime.py
output/e2e/20261017-main-29c67f4/venv/Scripts/python.exe output/e2e/20261017-main-29c67f4/browser_campaign.py smoke-resume
output/e2e/20261017-main-29c67f4/venv/Scripts/python.exe output/e2e/20261017-main-29c67f4/browser_followups.py regen
.venv/Scripts/python.exe output/e2e/20261017-main-29c67f4/controlled_campaign.py
.venv/Scripts/python.exe output/e2e/20261017-main-29c67f4/positive_note_regression.py --database-evidence
~~~

These record reproduction, not renewed paid authorization. Existing paid-attempt files prevent accidental repeats. Use a new run identity/bounded authorization, preserving this ledger. Keep failing-note expectations. Private runtime URLs are removed after owned cleanup; start another disposable runtime.

Original immutable packages/private bootstrap data are excluded from the sanitized artifact index. Secrets/cookies/proofs/signed URL queries are excluded from published evidence. Cleanup receipts identify only owned resources. AGENT.md/WORKLOG.md stay ignored; human/billable hours are unknown.

Both owned runtimes/containers were verified removed and all six test ports closed. End verification:16:02:20 MSK; HEAD and remote main still29c67f4. Recorded baseline-to-cleanup interval15:11:45–16:02:20 MSK includes setup/waits and excludes earlier discovery; it is not human/billable effort.

Limitations: incomplete requested repetitions and live Spanish/historical/race follow-ups; controlled semantic judgments; native-popup geometry; private emulated storage rather than production S3; no production migration, rollout or business signoff.

## 8. Ticket recommendations and direct answers

| Ticket | Recommendation |
|---|---|
|ANY-543|Not ready: false rejection, incomplete RU/ES publication and failed translation|
|ANY-635|Not ready: no completed live ES original/round trip; Spanish PDFs are controlled evidence|
|ANY-553|Not ready: second warm regeneration terminates; other repetitions incomplete|
|ANY-554|Not ready overall: manual price/missing-data improve; CO gates and post-rate archive remain|
|ANY-548|Candidate for focused persistence/isolation human acceptance: genuine automatic saves, complete restore/replay/ownership passed; disclose live-language/race limits and safe legacy retirement|

**Can a user complete the full tested workflow on current main?** A bounded English original→edited document→Copy/PDF→clean-login path completed. The complete multilingual/regeneration workflow did not:4/7 checks failed,1/2 regenerations failed,2/2 translations failed.

**Which original findings are resolved in observed behavior?** Manual USD binding survived3 live refreshes; missing fields are explained; edited Copy/PDF agree; successful checks automatically persist and restore; ownership/replay passed. Adversarial/heading fixes have controlled evidence, not universal live-resolution claims. The old undurable successful legacy route is safely retired.

**Which remain reproducible or unverified?** CO publication/ordinary-text false rejection; real review structure errors; generic and short-D1 translation blocked; post-rate archive409 controlled. The18-check matrix,9 sequential regenerations, genuine live Spanish round trip/reset, live historical regeneration/races and native popup clipping remain incomplete/unverified.

**Which can be submitted for human acceptance?** ANY-548 is the only focused candidate on the observed persistence evidence. The other four should not be submitted as passing. None of this establishes unconditional five-ticket end-to-end acceptance or production rollout.

