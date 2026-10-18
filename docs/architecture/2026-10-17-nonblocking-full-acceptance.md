# Nonblocking workflow acceptance — 17 October 2026

**Overall: FAIL for full acceptance; the ordinary live response → explicit agreement
→ edit → Copy/PDF → restore journey succeeds.** Diagnostic execution can still
delay newly queued user work. Selecting free work can leave contradictory paid
prose in the document. Multilingual and regeneration repetitions are incomplete
under the user's revised **50 physical external provider-call ceiling**.

This campaign tested the requested branch and current policy. It did not repair
product code or reinterpret diagnostic publication as satisfying older content
rejection requirements. No commit, push, merge, deployment or Linear write occurred.

## Baseline and provenance

- Branch: `codex/nonblocking-llm-workflow`; HEAD and fetched upstream:
  `bc458e28294fa02bf98c17e1ee9de9141899e5e9`.
- Stayed in the existing checkout. Fetched origin for context only; no pull,
  rebase, merge, worktree, stash or reset.
- Initial Git status contained four unrelated untracked design/acceptance
  documents and **zero uncommitted application files**. Their bytes, ignored
  AGENT.md/WORKLOG.md and local environment files were preserved.
- Frozen inventory: **609** application, test and configuration files. SHA256 of
  the canonical manifest:
  `a583d5df2ddb8ff23e5310faedc0be11a485c859ed95b556d50cf82b8ddd0b8d`.
  [Full baseline and hashes](../../output/e2e/20261017-nonblocking-bc458e2/baseline.json).
- Compared with implementation base `29c67f4580bea8a7d58530beaeea2abb537af1a9`, the
  branch changes 38 application paths, 20 test paths and four documentation paths.
  The complete classified manifest has SHA256
  `594c1fd609f2229d99fcb8b1ffb129232ead600e2a373bbed8cd044c563d59db`:
  [changed-file inventory](../../output/e2e/20261017-nonblocking-bc458e2/application-change-manifest.json).
  This is separate from the empty local application-change manifest.
- Final recheck: **no concurrent application changes, no tracked diff and no
  changes to preserved files**. [Recheck](../../output/e2e/20261017-nonblocking-bc458e2/source-recheck.json).

The execution [plan](plans/2026-10-17-any-543-635-553-554-548-nonblocking-full-acceptance.md)
preceded execution. Read the latest 17 October design clarification, implementation
record and both follow-ups, preceding main acceptance, ownership/workflow and
worker deployment guidance. Current implementation supersedes historical migration
targets still shown in older Compose overlays; those overlays were not deployed.

All five Linear descriptions and all returned discussion pages were read. The
latest Mikhail Gushinets comments were dated 15 October; pagination was exhausted.
The five complete 15 October attachment ZIPs were fetched afresh and matched their
published hashes. Original JSON candidates, before/after states, inputs and short
D1 data were inspected, as were original D1 PDF rendering, missing-data UI and
failed M1 screenshot. [Provenance](../../output/e2e/20261017-nonblocking-bc458e2/attachment-provenance.json).
The older 8/11 October multimedia attachments were not exhaustively re-downloaded.
The reviewed QA inputs are synthetic/reconstructed contracts, not original customer
contracts; original customer contracts/conversations were unavailable.

## Runtime and isolation

Production frontend was built from a verified isolated copy of frozen frontend
sources, sharing installed dependencies without changing the user's existing
build. Next.js 16.3.0, Node 24.19.0, build `oGamhFIfS-wSOqct6kAza`; webpack build
passed. `next start` served it successfully but emitted the existing standalone
output warning. This is not deployment/container acceptance. The build skips type
checking by existing configuration; a new full type/lint suite is not claimed.

API and the existing LLM/export worker entrypoints used the same frozen repository
sources. Python 3.12.10; OpenAI 2.43.0, LiteLLM 1.89.3, Pydantic 2.13.4,
PydanticAI slim 2.2.0, SQLAlchemy 2.0.54, psycopg 3.3.6, ReportLab 4.5.1.
PostgreSQL 17.11, owned disposable container, guarded migration to the discovered
single head **0007_nonblocking_llm**. No existing application database was used.

Owned frontend/API/private S3 emulator ports: **13174/18174/19174**. Actual
S3ObjectStorage and ExportWorker produced browser downloads through a private
synthetic Moto bucket. This verifies the application storage protocol, not external
production S3. Chromium used independent contexts and real register/login forms.

Effective runtime: workflow_v2 and llm_workflow true, exact loopback Origins,
matching synthetic auth, prompt `workflow-v7-nonblocking`, diagnostic contract
`diagnostics-v1`, requested/returned **gpt-6-luna**. Inherited local configuration
had gpt-5.6-luna, flags false and no pricing bounds; explicit isolated process
overrides selected the user-requested model and workflow. No configuration file
was changed. Diagnostics remained enabled throughout.
[Sanitized runtime](../../output/e2e/20261017-nonblocking-bc458e2/effective-runtime.json),
[database image](../../output/e2e/20261017-nonblocking-bc458e2/postgres-image.json).

## Requirement matrix

PASS below applies only to the stated layer and sample. Partial rows explicitly
retain BLOCKED/NOT RUN subcases rather than implying complete acceptance.

| Requirement | Live browser/API result | Controlled result / remaining coverage |
| --- | --- | --- |
| A1 register/login and required/optional project fields | PASS: real forms and field guidance; optional client/email/end date blank | Existing auth integration tests PASS |
| A1 main analysis + three replies + automatic History | PASS, 6/6 checks; first main had no agreement or agreement call | Transactional publication tests PASS |
| A1 removed explanation/citation/context blocks and diagnostic warnings | PASS in inspected main UI; no absent-document placeholder/error | Six frontend workflow/result tests PASS |
| A2 RU/EN × RU/EN/ES | All six combinations completed once; language prose follows interface/client selection | **12 of 18 requested checks BLOCKED by budget**; verdict quality differs in one case |
| A3 warm/neutral/firm regeneration | PASS selected-only replacement, analysis/agreement retention; warm 3, neutral 1, firm 2 including historical case | **3 of 9 requested repetitions budget-blocked**; content findings below |
| A3 manual replacement confirmation | PASS actual cancel kept edited text and sent no generation; accept replaced it | Controlled provider failure preserves old reply |
| A3 historical scope | PASS after changing current scope to include Arrow/email: regeneration retained original exclusion | Frozen source verified; stale current-scope archiving returned 409 |
| A4 translate without agreement | PASS: replies-only EN→ES; no agreement created; original analysis/History retained | Native schema and persistence tests PASS |
| A4 edited agreement ES→EN→ES | PASS 2/2 agreement translations; saved prose used; hours, amount, currency and schedule meaning retained | Faithful hours parser case remains diagnostic rather than a gate |
| A4 controls and restoration | PASS desktop/390px, readable names, focus and keyboard; no horizontal overflow; saved selection restored by clean login | Fresh language selection for a new complaint after manual override was not exercised as a separate live paid check |
| A5 explicit preparation/reload/replay | PASS: one live preparation; no prior CO call; current pricing used; reload/replay did not regenerate or erase edits | Simultaneous same-revision coalescing, newer revision conflict and failure isolation PASS in PostgreSQL tests |
| A5 loading isolation during slow agreement | NOT RUN as a separately captured live slow-provider browser case | Completed main response/History survive controlled agreement failure; this is narrower than observing every loading control |
| A6 estimate provenance/current terms | PASS live fixed USD600 snapshot → current hourly 60EUR agreement → three 80EUR refreshes → 90EUR refresh available; original analysis unchanged | Exact hourly rate A30→B60 admission/provenance tested in controlled PostgreSQL, not a separate live initial check |
| A6 manual commercial conditions | PASS 3/3 refreshes kept 2.5h/175.35USD and schedule; currency-only edit retained amount; explicit 2.5×80=200EUR exported | Live free-work stale rationale **FAIL F2** |
| A6 stale protection | PASS rate-only edits could archive/export manual terms; actual scope change rejected archive with analysisStale | Current commercial signatures and saved source provenance match inputs |
| A7 missing data | PASS separate/combined guidance, persisted clearing/reload, incomplete Copy/preview and optional blank email/date | Missing-data PDF helper timed out after finalization did not expose a PDF action; no missing-data download claimed; exact field-error HTTP body was not retained |
| A7 Copy/PDF | PASS 7 actual browser downloads, 9 rendered/inspected pages; EN/ES document labels, RU/ES glyphs and three-page continuation | Pure RU-label browser PDF NOT RUN; free-work PDF content contradiction retained |
| A8 History/reload/clean login | PASS server restore, History read-only and later document edits retained; original snapshots unchanged | Historical-format and older-completion/newer-request tests PASS |
| A8 close tab and recovery | PASS tab closed while live regeneration status was running; clean login recovered succeeded result | Service cancellation/restart checks PASS |
| A8 lost response/key conflict | PASS same successful check replay, actual lost replay response and same-key recovery; changed payload 409, no extra calls | New keys with identical text covered in worker tests; live identical-text repetition budget-blocked |
| A8 owner isolation | PASS **35 positive-owner routes**, foreign 404, anonymous 401; foreign PUT 404 | Projects, drafts, analyses, History, operations, agreements, exports and downloads included |
| A8 retired legacy routes | No live legacy generation dispatched | Current API integration verifies stable owned context required; no undurable fallback PASS |
| B retained problematic text | — | **25/25 exact retained candidates published**, diagnostics recorded; no diagnostic document overwrite |
| B reviewer rejection/malformed paths/outage/retry | — | PostgreSQL matrix PASS for rejection, candidate.text, candidate.labels.clientEmail, outage and retry; both pricing variants |
| B diagnostic budget/restart/duplicate/leases | — | PASS budget exhaustion, cancelled review restart without redispatch, duplicate no-op, exclusive claim and epoch fencing |
| B independent scheduling | — | **FAIL F1:** new user execution waited behind an already running held review |
| Genuine provider/structure failures | All 19 live operations succeeded | Native HTTP 503 regeneration/agreement and malformed/missing generator outputs correctly FAILED and retained prior material/History |
| Persistence failure | No live DB failure induced | Existing native pipeline transient publication/cancellation tests PASS; no application DB fault injection |
| OS-level graceful worker shutdown | Owned processes stopped after jobs completed | Full 30-second signal/drain behavior NOT RUN; cancellation/recovery probe is narrower |

## Product failures against the requested acceptance

**F1 — diagnostic execution blocks new user execution.** `B-scheduling-single-worker`,
frozen HEAD/manifest above, real PostgreSQL/current worker/gateway with controlled
provider (fixture model identifier gpt-5.4-nano; zero external sends). After main
publication the diagnostic provider entered an explicit synchronization barrier.
A regeneration was then admitted. During a five-second bounded observation it
remained queued and never entered the provider. Releasing the diagnostic let it
succeed; original main result remained intact. The expected user completion before
diagnostic release was not met. This proves delay behind a running diagnostic,
not indefinite starvation or a failure to save the already completed result.
[Exact events/statuses](../../output/e2e/20261017-nonblocking-bc458e2/scheduling.json).
Queue priority is insufficient to preempt work already running on the single worker.

**F2 — free-work selection retains stale paid manual rationale.** On the live
agreement, enter explicit 2.5×80=200EUR rationale, then select No additional charge.
The fee becomes free, but Copy and the actual downloaded PDF still display the
200EUR paid rationale below it. The saved amount/currency also remain 200/EUR.
The rationale was manual, not a hallucinated model response; this finding is about
reconciling the explicit free-work action with existing paid prose. No code or
assertion was changed to obtain a pass. [Saved state and clipboard](../../output/e2e/20261017-nonblocking-bc458e2/free-live.json),
[actual PDF](../../output/e2e/20261017-nonblocking-bc458e2/free-live.pdf).

## Content quality, separately from publication policy

- Scope expectation matched **5/6 main checks**. RU/RU threshold 5%→3% plus existing
  price formatting was expected in_scope from the explicit terms. The model returned
  borderline because the source did not say whether the single revision round had
  been used. This is the observed mismatch to the pre-dispatch oracle, not a claim
  that a human could never request that clarification.
- Summary/reasoning/suggestion use the expected UI language in this sample.
  Replies use the expected client-language prose, with legitimate names, URLs,
  email/technical identifiers and some verbatim English scope quotes. In particular,
  all three RU/ES Instagram replies contain an English exclusion quotation; do not
  describe those strings as exclusively Spanish under a literal older criterion.
  No unquoted Russian leakage was observed in the two Spanish main groups.
- All **6/6 regeneration texts changed**, and only the selected tone was replaced.
  This does not prove substantive novelty: live semantic diagnostics flagged
  cosmetic_reply on **3/6** (warm-3, firm-1, historical firm). These are reviewer
  findings, not independently established objective novelty failures.
- **2/6 regenerations** (firm-1 and historical firm) offered original AI terms
  6h/USD180 while the edited agreement held 2.5h/USD175.35. Structured agreement
  values remained intact; generated prose was commercially inconsistent. Historical
  firm received commercial_terms diagnostic; firm-1 received only cosmetic_reply,
  illustrating incomplete diagnostic detection. Warm variants also varied between
  omitting commercial values and using the saved manual proposal.
- All **3/3 translations** completed without structure correction. Edited numeric
  values survived both agreement translations. ES schedule moved from días
  laborables to business days and back to días hábiles, retaining working-day and
  approval meaning. No translation-content discrepancy was confirmed in this short
  D1 sample. There was no mandatory content-repair loop.

The live diagnostic corpus has 59 observations: **42 pass, 16 finding, 1 uncertain,
0 diagnostic_error**. Rules include commercial_terms 8, cosmetic_reply 3,
scope_position 3, numerical_terms 1, currency 1 and uncertainty 1. These are
field-level observations, not 17 independent failed operations, nor a reliable
false-positive/false-negative rate. [Full typed observations](../../output/e2e/20261017-nonblocking-bc458e2/diagnostic-observations.json).

## Original Mikhail findings and changed policy

| Original evidence / ticket | Current observation | Older rejection criterion |
| --- | --- | --- |
| D01 CO/short-label language gate, ANY-543/635/554 | Main publishes without CO; explicit agreement and ordinary English note controlled checks succeed | Earlier combined-response gate deliberately removed |
| Invalid reviewer paths, ANY-543/635/553/554 | Malformed paths become diagnostic errors in controlled PostgreSQL; completed operation survives | No generator failure/retry required under new policy |
| D02 EN/RU or Hola+RU, ANY-543/635 | Exact retained mixed candidates publish with separate findings | **Not satisfied** if old requirement demands rejection |
| D03 scope reversals, ANY-553 | Retained excluded-free/included-paid/ambiguous-certain candidates publish; findings retained | **Not satisfied** by recording a finding |
| D07 cosmetic regeneration, ANY-553 | Retained cosmetic candidates publish; 3 live cosmetic reviewer findings | **Not satisfied** if old requirement demands a corrected replacement |
| D09 translation/hours, ANY-635 | Live edited D1 translations complete; exact 12 horas adicionales replay remains diagnostic | Old parser blocking no longer applies; content correctness still assessed separately |
| E1 manual USD→EUR overwrite, ANY-554 | 3 live refreshes keep 175.35USD despite current 80EUR/hour; AI proposal separate | Manual preservation satisfied in tested path; F2 remains |
| D08 missing-data explanation, ANY-554 | New editor/Copy/preview explain all cleared required fields | Tested guidance improved; incomplete browser PDF not claimed |
| D05 History loss, ANY-548 | 6 main checks auto-save History before agreement; clean login restores | Tested new workflow satisfies automatic persistence; legacy deployment not certified |

## Counts, accounting and latency

Fresh authorization was requested and received in this chat, then narrowed to 50
before any paid send. The historical allowance was not reused. One SQLite ledger
covered API/worker processes and post-publication diagnostics. A no-network attempt
to reserve after 50 was rejected with the count still 50; ledger was not reset.

| Live operation | Succeeded / attempted | Generator calls | Admission-to-finish min / median / max seconds |
| --- | --- | ---: | --- |
| Main check | 6/6 | 12 | 7.99 / 16.73 / 21.60 |
| Explicit agreement | 1/1 | 2 including refreshed estimate | 10.78 / 10.78 / 10.78 |
| Translate | 3/3 | 5 | 6.44 / 6.83 / 15.34 |
| Estimate refresh | 3/3 | 3 | 5.91 / 7.53 / 9.34 |
| Regenerate | 6/6 | 6 | 5.70 / 7.89 / 13.00 |
| Separate diagnostics | 19/19 | 22 review calls | 3.04 / 8.20 / 19.20 |

**19/19 live user operations first-attempt successful; 28/28 generator stages on
first structure attempt; zero structure-corrected successes, zero genuine live
terminal failures and zero transport retries.** These overlap the scenario matrix
and must not be counted again by ticket. Agreement completion sample is one.

**50 external physical sends = 28 generation + 22 diagnostics**, all requested and
returned gpt-6-luna. Paid dispatch window: **19:43:36–19:58:33 Moscow**. Provider usage:
99,084 input, 24,492 output, 20,807 cached input and 18,895 reasoning tokens; cached
and reasoning counts are subsets, not additional totals. Conservative configured
bounds USD0.0000003/input and USD0.000001/output produce **USD0.0542172** for all
reported usage; unknown-usage dispatches: zero. This is conservative estimated
cost, not an invoice. Bounds exceed the published standard text prices checked on
the [official model page](https://developers.openai.com/api/docs/models/gpt-6-luna).

All 50 wire responses join their persisted provider-call rows, decoding LiteLLM's
wrapped response IDs. Active-case labels can advance before an earlier diagnostic
dispatch; totals use the authoritative joined operation, not that label.
[Accounting](../../output/e2e/20261017-nonblocking-bc458e2/provider-accounting.json).
The actual marketing source projection contains **19 user operations, zero
diagnostic outcomes and all 50 provider calls**.
[Metrics proof](../../output/e2e/20261017-nonblocking-bc458e2/metrics-projection.json).

Controlled results remain separate: 25 retained candidate cases, three lifecycle
probes and four native HTTP/structure failures used zero external sends. In the
four failure cases, 503 regeneration/agreement each used two bounded attempts;
malformed JSON and missing required fields each used three. All failed as expected
with prior material and History preserved. The scheduling independence assertion
failed and is retained rather than relabeled green.

Unchanged targeted backend invocations passed **12 + 53 + 16 + 59 tests**; frontend
6 passed and persistent guard 5 passed. This is not a full-suite or deployment
pass. Original attempts and harness failures remain: sandbox temporary-file denial,
two wrong test-module paths, Windows event-loop setup, UTF-8 harness decoding,
wrong project update method, completed replay shape, protected fixture fields,
historical null agreement, and collection-key/response-ID normalization. Paid
successful stages were resumed from saved state rather than silently regenerated.

## Browser/export evidence and cleanup

Seven PDFs were actually downloaded by browser download events from durable worker
exports: D1 ES, translated EN, translated-back ES, post-rate D1, explicit 200EUR,
free work and a three-page multilingual document. All nine pages were rendered and
visually inspected. Numbered long paragraphs 01–45 occur once each; no clipping,
missing or duplicated continuation was observed. RU Cyrillic and ES accents/
inverted punctuation render correctly. English and Spanish labels were exercised;
pure Russian labels were not. The free document's financial contradiction is F2,
not a rendering success that cures its content failure.
[PDF inspection](../../output/e2e/20261017-nonblocking-bc458e2/pdf-visual-review.json),
[long downloaded PDF](../../output/e2e/20261017-nonblocking-bc458e2/long-multilingual-live.pdf).

Only owned services/resources were stopped. Ports 13174/18174/19174 were verified
closed; the exact owned runtime PostgreSQL container was verified absent.
Disposable test databases/containers used ownership-checked context cleanup.
No Docker Desktop restart or user's-stack action occurred. The new private
connection bootstrap was deleted. Frozen source/build copies, sanitized evidence
and the exhausted ledger are retained; original local configuration and ignored
journals remain unchanged. [Cleanup proof](../../output/e2e/20261017-nonblocking-bc458e2/cleanup-verification.json).

## Direct acceptance answers

1. **Can the user complete response → agreement → edit → Copy/PDF → restore?** Yes,
   observed on a genuine live predecessor through actual downloads and clean login.
   This does not cover every requested language/repetition or free-work content.
2. **Can diagnostics block publication or starve user execution?** Completed parent
   publication survives findings/errors. An already running diagnostic **can delay
   new user execution** on the single worker; independent scheduling failed F1.
3. **Are provenance and manual conditions preserved?** Structured provenance,
   175.35USD binding, effort and schedule survived the tested refresh/translation/
   restoration path. Free-work rationale conflict and regenerated prose remain.
4. **What product failures remain?** F1 diagnostic scheduling delay and F2 stale paid
   manual rationale retained by free-work selection. No source repairs were made.
5. **What content issues remain?** One of six scope-oracle mismatches, two of six
   regeneration commercial mismatches, three cosmetic diagnostic findings, and
   English contract quotations inside Spanish replies under older strict wording.
6. **What can be submitted for human acceptance?** This frozen source/report plus
   the successful live core flow, persistence/isolation, provenance/manual-value
   evidence, controlled diagnostic isolation and actual PDFs. **Do not submit a
   blanket PASS**: F1/F2 and the explicitly budget-blocked/unexecuted coverage need
   owner review, and conflicting older Linear rejection criteria need reconciliation.
