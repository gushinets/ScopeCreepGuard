# Design refinement and contextual onboarding

Issue: user-requested application design and first-use onboarding (no issue ID).
Base: freshly fetched `origin/main`, f3e34de. Branch: `codex/design-onboarding`.
Checkout: clean original main; fetch and separate branch, no reset, push or PR.

## Evidence and direction

The implementation is React/Vite, despite the retained Next.js instructions.
No installed Next.js package is present. Existing workflow and ownership documents
define project, draft, immutable history, analysis and agreement boundaries.
The current request overrides historical guidance to hide assessment rationale.
No mockups were attached to this chat; the repository contains an assessment
screenshot under architecture/evidence. No required alternate-branch work was
identified in the branch/log inspection. Docusign is a reference for restrained
typography, confident accent color and clear task hierarchy, not product claims.
Impeccable context launcher could not install its engine; inspect source directly.

## Scope and exclusions

Refine shared tokens, controls, authenticated navigation, auth screens and copy
across existing screens. Retain complete rationale, client language/tone controls,
regeneration, estimates/currencies, agreement preparation, History and Drafts.
Add optional contextual guidance tied to real project and analysis actions.
No onboarding settings/restart, business-rule changes, paid AI verification,
testimonials, new product claims, AGENT.md/WORKLOG.md publication, push or PR.

## Ordered implementation

1. Extend existing profiles with minimal status/step state through Alembic.
   Existing rows are completed (exempt); new profiles start not_started.
   Preserve the repository's schema catalog verification and migration boundaries.
2. Add authenticated onboarding read/transition API through profile service and
   repository. Serialize transitions with a profile row lock; terminal states
   never reactivate and stale steps never regress. Repeated requests are safe.
3. Add a fail-open authenticated onboarding provider. Guide opening the create
   form, saving scope/project, submitting a check, and viewing its successful
   assessment/reply. One in-flow tooltip by its target, no focus theft or overlay.
   Skip lives near the top of desktop left navigation and mobile navigation.
4. Apply shared restrained surfaces, purple accent, typography, form/focus/button
   rules and responsive shell. Refine EN/RU copy using Sepia, preserve factual text.
5. Add transition/persistence tests and frontend action/failure coverage. Run
   Docker checks and inspect real browser journeys with controlled AI responses.
6. Capture desktop/mobile and EN/RU screenshots; record actual results below.

## Verification and handoff

Required: new/existing users; skip at each step; reload/relogin; terminal-state
race; failed saves/checks; state outage; shared screen consistency; rationale,
reply controls and agreement actions. Docker tests plus browser journey required;
build alone is insufficient. Use a disposable database and controlled AI.

Owner: current implementation chat. Record evidence and any environment limits
here before handoff. Missing attached mockups are a known input limitation.


## Rebuild after design review — 22 October

The user rejected the first styling pass and in-flow hint boxes. Replace that UI
with the explicitly requested design-taste-frontend workflow; retain the profile
migration, ownership-safe API and domain behavior. No new branch/reset is needed;
the current branch contains this chat's work only.

Direction: Framed sheet, seed 312194846. Chosen from builder directions because
this is a document workbench, not a dashboard. No redraws. Load IBM Plex Sans,
replace the violet accent with the dealt teal and near-black primary controls.
Use the product's scope boundary as its signature: the original agreement and the
new request stay visibly distinct, with assessment evidence beside the response.

Data inventory: authenticated owner; projects with scope/industry/dates; optional
client details; hourly/fixed prices and currencies; mutable request text; immutable
assessment/verdict/confidence/rationale/citations; preliminary estimate; editable
reply with independent client language and tone; separately prepared agreement;
saved History snapshots; working Draft revisions. No vanity data or new claims.

Screen questions: auth—how do I access my work? first use—what do I need first?
project—what did we agree? check—does this request fit? result—why, and how do I
reply? agreement—what am I proposing? History—what did that check say? Drafts—what
am I still editing?

Order: rebuild tokens/brand/frame/mobile navigation; project and request surfaces;
assessment/reply/agreement grouping; History/Drafts/auth; then contextual coaching.
Use a single anchored coachmark, target highlighting and a truthful task trail.
Desktop coachmarks occupy reserved space beside targets; mobile ones remain in
flow adjacent to controls. No backdrop, focus theft, duplicate Next, settings or
restart. Preserve database authority and terminal-state protections.

Acceptance: before/after inspector at 1440/768/390; written screenshot critique;
Docker unit/integration checks; real first-use, skip, reload/sign-in, failure and
state-outage journeys with a controlled worker. Record measured limitations.

## Implementation and verification record

Implemented the rebuild direction above, superseding the initial purple styling
and simple hint treatment. Shared framed-sheet tokens, self-hosted IBM Plex Sans,
responsive navigation, structured project forms, scope/request comparison,
complete assessment/reply surfaces and a full-width agreement editor are in place.
Contextual guidance uses one target-linked coachmark and a real-action task trail,
with no focus theft, blocking overlay, duplicate Next, settings or restart.

Alembic 0008 adds status/step to existing profiles, exempts old profiles and starts
new profiles as not_started. Authenticated GET/POST profile onboarding endpoints
use the existing service/repository boundaries and terminal-safe row locking.
OpenAPI, frontend types and exact schema verification are updated.

Docker verification: 354 frontend tests passed (one existing Python/JOSE interop
file excluded), eight new backend transition/PostgreSQL tests passed, TypeScript,
production build, frontend lint/boundaries, changed Python lint, OpenAPI/type
checks and Git whitespace check passed. The full backend suite was not run.

Browser verification includes the complete real-action journey, keyboard start,
failed validation/checks, skip at all stored stages, reload and sign-in persistence,
separate browser context, stale-tab protection, guidance outage, Russian rationale
with independent Spanish replies/regeneration, agreement preparation and saved
History rationale. Final desktop/tablet/phone inspection has no failures; sparse
desktop canvases and the bounded auth layout retain documented spacing warnings.

Evidence, screenshots, critique, test scope and limitations:
[Design and onboarding verification](../evidence/2026-10-22-design-onboarding/README.md).
Known limits include the unrun full backend/PDF/provider checks, the existing
cross-account Draft URL error, a bundle-size warning, and missing attached mockups.
Review/merge and broader CI belong to the repository owner. Branch remains
codex/design-onboarding with uncommitted changes; no push or PR was requested.
