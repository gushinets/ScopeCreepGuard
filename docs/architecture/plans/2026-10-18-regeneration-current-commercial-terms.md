# Regeneration current commercial terms

- Base/branch: fetched origin/main and HEAD `d3544de`, existing `main` checkout.
  Untracked evidence/design documents make the tree non-clean; preserve them and
  remain on this branch. No reset, stash, worktree, commit, push or database migration.
- Scope: explicit frozen regeneration authority, provider/reviewer projection and
  prompt version. No price history, LIFO, content gate or repair loop.
- Evidence inspected before implementation: slot-11.json frozen_input and actual
  provider-outputs/0042.json. Saved 2.5h/175.35 USD coexists with historical
  reasoning proposing 3.5h and project rate 30 USD. Saved schedule, free selection
  and additional terms are omitted from the provider projection; authority is unclear.
- Steps: freeze authoritative terms; project scope, current terms and previous
  wording separately; align diagnostic inputs; version prompt; test provider
  requests, preservation and replay; record results below.
- Older queued operations: existing version fencing fails unsupported v7 pending
  stages with workflowVersionUnavailable before provider dispatch. Never rewrite
  their frozen inputs/history. Completed replay remains stored; new submissions
  capture v8 inputs. Deployment owner should drain v7 work before rollout when possible.
- Verification/limitations: controlled tests only; no live paid calls authorized.
  Implementation owner: this change; live confirmation requires separate approval
  covering at most one regeneration per tone and diagnostic calls.


## Implementation and handoff

Before: provider JSON used `project` (historical rates), `analysis` (scope narrative
including old commercial proposals), and `document.reply` / a partial
`document.changeOrder`. Actual call 0042 omitted saved schedule, free choice and
additional conditions. The generic preservation instruction gave these competing
facts no clear order of authority.

After: admission captures `currentCommercialTerms` in the immutable operation
input. Provider and semantic reviewer receive identical `scopeContext` (historical
scope, verdict, citations, additional-work applicability), `currentCommercialTerms`
(saved effort, amount, currency, free flag, schedule, end date and additional terms,
with source/preliminary markers), and `previousReply` (selected wording/tone).
Historical commercial narrative and project rates are absent from this projection.
A present agreement, including empty/missing fields, never falls back to estimates.
Only absent agreements use the existing analysis estimate, explicitly preliminary.
Full historical analysis/project/document snapshots are preserved unchanged.

Prompt rules require rewriting only the selected reply, retaining accepted scope,
using saved terms over previous prose, no rate recalculation or restoration of
cleared terms, no payment demand for free work, and mentioning terms only when useful.
Local diagnostics use the same authoritative fields, with free saved amounts treated
as nonpayable. Semantic review receives no competing aiValues or savedDecisions for
regeneration. Existing diagnostics remain nonblocking; no repair loop or new regex
content gate was added.

Verification:
- Focused unit/review/diagnostic/API-contract set: 143 passed. Final commercial test
  file after adding the free-diagnostics case: 23 passed (144 distinct unit cases
  across these focused files).
- Affected PostgreSQL integration files: 17 passed, controlled providers only.
  Strengthened selected-text-change assertion additionally passed the
  True-malformed case. Tests check actual requests, frozen admitted terms, historical
  scope, selected-tone publication and preserved other state, same-key replay with
  no duplicate provider dispatch, and old-version refusal before dispatch.
- Mypy: success, 227 source files. Ruff lint/format and diff whitespace checks pass.
- OpenAPI export parity and generated TypeScript API contract parity pass.
- Initial integration attempts encountered sandbox Docker denial and incorrect
  harness cwd; rerun from backend with owned disposable PostgreSQL succeeded.
  No application database or historical evidence was migrated/rewritten.

No live paid verification was performed. Controlled tests establish supplied inputs
and persistence behavior, not real-model compliance. Optional live follow-up is at
most three regenerations (one per tone) against one edited saved agreement, only
after explicit authorization covers generation, diagnostics, retries and cost/call
limits. No historical paid-call authorization is reused.

Changes are uncommitted on the preserved checkout. AGENT.md and WORKLOG.md remain
ignored; unrelated untracked acceptance/design documents remain untouched.
