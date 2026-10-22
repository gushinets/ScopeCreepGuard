# Design rebuild and onboarding verification

Historical iteration: the onboarding presentation below is superseded by the
[single walkthrough](../2026-10-22-single-onboarding-guide/README.md).

Verified locally on 22 October 2026, branch `codex/design-onboarding`, based on
freshly fetched `origin/main` f3e34de. Changes are uncommitted; no push or PR.

## What changed

The design-taste-frontend direction is **Framed sheet**, seed 312194846, retained
in [direction.json](direction.json). IBM Plex Sans is self-hosted under its OFL
license. Shared tokens, a document/shield mark, quieter controls and a responsive
navigation frame now connect auth, first use, projects, request checking,
assessments, replies, agreements, History and Drafts. No new profile screen or
onboarding settings were invented. Impeccable guided consistency and accessibility;
Sepia guided concise EN/RU copy. Docusign informed the restrained document-oriented
hierarchy. Illustrative scope/request content is explicitly labelled as an
example; there are no invented customers or performance claims.

The assessment keeps its full rationale, citations, suggestion and preliminary
estimate. Replies retain tone, editing, copy, regeneration and independent client
language. Agreement preparation opens a full-width editing/preview workspace.
History remains saved snapshots; Drafts remain working material. Pricing,
currency, generation prompts and analysis rules were not simplified.

## Database and API

Alembic `0008_contextual_onboarding` extends existing `profiles` with
`onboarding_status` and `onboarding_step`, constrained to valid combinations.
Existing profiles become `completed/4` (exempt from automatic onboarding); new
profiles default to `not_started/0`. No timestamps are needed for this flow.

Authenticated `GET /api/v2/profile/onboarding` reads state. `POST` accepts
`form_opened`, `project_saved`, `check_submitted`, `result_viewed` or `skip`.
The existing profile service/repository owns the operation. Updates lock the
current owner's row; repeated/out-of-order events are safe and completed/skipped
states cannot reactivate. No client-supplied user ID or duplicate user system.
OpenAPI, generated frontend types and the exact schema catalog were updated.

The browser reads backend eligibility, queues transitions and retries failed
state writes on focus/reconnection. Guidance failures do not block normal work.
Skip dismisses immediately and persists through the API. No localStorage
eligibility, slideshow, duplicate Next button, restart or toggle was added.
Coachmarks attach to the current action, with collision-aware desktop placement
and adjacent normal-flow placement when space is insufficient, including phones.
They describe targets without moving keyboard focus.

## Checks actually run

| Check | Result |
| --- | --- |
| Docker production build and TypeScript | Passed; existing large bundle warning remains |
| Frontend ESLint and dependency boundaries | Passed, 94 modules |
| Frontend Vitest | 354 passed, 49 files; Python/JOSE interop file excluded |
| Final copy regression check | 17 History/agreement tests passed after updating the action-label expectation |
| New backend onboarding tests | 8 passed: ordered/idempotent transitions, migration exemption, new profiles, isolation, persistence and concurrent terminal updates |
| Ruff on changed Python implementation/tests | Passed |
| OpenAPI export check and generated API type check | Passed |
| Git whitespace check | Passed |
| Static taste scan of 15 changed UI files | 0 failures; 6 warnings explained below |

The backend tests used the existing pytest stack against PostgreSQL 17 in an
owned Docker test database. A small local fixture supplied disposable databases
on the isolated Compose network rather than launching nested Docker from a test
container. This caused one harmless unknown integration-mark warning in that
temporary harness. The full backend suite was not run.

The excluded frontend test is `src/test/draft-proof-interop.test.ts`: its existing
cross-runtime verification requires Python/uv in the Node-only frontend image.
No claim of a complete CI run is made.

## Browser journeys

All checks used the Docker-served production application on port 3100. Controlled
structured responses ran through the existing durable AI worker/pipeline; no
paid provider calls or real API key were used.

| Journey | Observed result |
| --- | --- |
| New authenticated user | One contextual tip, visible Skip and task trail |
| Keyboard start | Focus Create project, press Enter, enter the real form; guidance does not steal focus |
| Invalid project form | Validation shown; onboarding remains at scope step |
| Successful project save | Advances to the actual request field |
| Failed check (controlled 503) | Request retained; onboarding does not advance |
| Successful check | Full assessment/reply rendered; state becomes completed; one completion tip |
| Prepare agreement | Real workflow produces persisted editable terms and document preview |
| Reload after completion | Guidance stays dismissed; result/agreement remain |
| Skip at steps 0, 1, 2, 3 | Actual UI Skip immediately dismisses; database state persists after reload and UI logout/sign-in. Each state was seeded through the authenticated transition API for this matrix |
| Separate browser context/sign-in | Completion remains terminal without relying on browser storage |
| Stale tab event | `form_opened` cannot reactivate completed state; reload shows no guide |
| Guidance endpoint unavailable | Project form remains accessible and editable on a phone |
| Existing users | PostgreSQL migration test confirms exemption; browser confirms terminal states do not display guidance |
| Russian interface + Spanish client language | New Russian rationale remains Russian; Spanish replies translate/regenerate; agreement preparation and reload work |
| Desktop/tablet/phone | Layouts checked at 1440, 768 and 390px; Russian phone overflow found and fixed |
| History | Full archived rationale, saved scope and reply can be opened without replacing the working Draft |

The final browser run covered the complete real-action journey again after the
layout rebuild. The flow remains understandable after immediate Skip: ordinary
labels, the initial scope/request example, validation and result headings remain.

## Screenshots

| Screen | Evidence |
| --- | --- |
| Sign-in and registration | [Desktop](screenshots/final-login-desktop.png), [phone](screenshots/final-login-mobile.png), [registration](screenshots/final-registration-desktop.png) |
| First action + task trail | [Desktop](screenshots/final-onboarding-start-desktop.png) |
| Agreed scope guidance | [Desktop](screenshots/final-onboarding-scope-desktop.png), [phone](screenshots/final-onboarding-scope-mobile.png) |
| Client request guidance | [Phone](screenshots/final-onboarding-request-mobile.png) |
| Assessment ready | [Phone](screenshots/final-onboarding-ready-mobile.png) |
| Workbench + agreement | [Full desktop](screenshots/final-workbench-agreement-desktop.png), [tablet](screenshots/check-tablet.jpg) |
| Russian rationale + Spanish reply | [Phone](screenshots/final-russian-assessment-mobile.png), [full desktop agreement](screenshots/final-russian-spanish-agreement-desktop.png) |
| Projects | [Desktop](screenshots/projects-desktop.jpg), [phone](screenshots/projects-mobile.jpg) |
| History | [Full saved check](screenshots/final-history-detail-desktop.png), [phone rationale](screenshots/final-history-detail-mobile.png) |
| Drafts | [Desktop](screenshots/drafts-desktop.jpg), [phone](screenshots/drafts-mobile.jpg) |

## Visual review

The unmodified taste inspector checked public auth at all three widths.
Authenticated screens used its original browser probes and rules inside an
isolated authenticated browser, without a session proxy. Marketing-title rules
are replaced by the app's 18–28px title rule. Reports are in [inspection/](inspection/).
Final runs have no failures. Auth has two desktop spacing warnings; short
Projects/Drafts lists and unselected History have desktop canvas/panel warnings.
Their frames retain honest empty space when there is one saved item. No fake
rows or decorative filler were added to satisfy a density measurement. The
large internal gap before the footer was removed.

Static scan warnings: two unused mono theme definitions; one shadow on a floating
coachmark; three existing loading skeleton pulses. The UI uses IBM Plex Sans for
prose, no decorative gradient/glow, and respects reduced motion.

ROUND 1 — final rebuilt screenshots

Seen in one second: a scope-check workbench with a clear project and verdict.
Idea (one sentence): keep the saved agreement and incoming request visibly distinct,
then show evidence, the response and the proposed document in order.
Live thing: checking a real request and editing its reply/agreement.
Layout words by section: auth=split / first-use=example / projects=rows /
check=comparison / result=evidence / agreement=editor-and-paper / history=master-detail.
Scores: design 7 · usability 8 · creativity 7 · content 8 → overall 7.4.
Caps applied: creativity capped at 7 because the document-workbench approach also
fits a close competitor; app-screen exceptions apply to borders, labels and the
absence of decorative photography.
Top three problems, each with evidence and disposition:
1. Russian result controls forced a wider grid on phones
   (`final-russian-assessment-mobile.png`). Fixed the grid's intrinsic minimum;
   shipped build measures 390px content at a 390px viewport.
2. A one-row Draft list left a 656px internal gap before its footer
   (`drafts-mobile.jpg` / inspection). Removed forced main-region stretching;
   content and footer now follow normal flow.
3. Auth's centered access column leaves generous space on a large display
   (`final-login-desktop.png`). Retained a bounded readable form and labelled
   example; the phone puts access first. This remains a measured warning.

## Limits and follow-up ownership

No attached mockups were available; the repository's older assessment image and
the supplied Docusign reference were inspected. No real-provider quality or
payment test was needed or performed. PDF export workers/finalization were not
retested end-to-end; agreement preparation, editing surfaces and preview were.
The build reports a 619KB JS bundle before gzip; code splitting is outside this
change. The local Vercel analytics script returns 404 without a Vercel deployment.

An existing account-switch edge remains: signing into a different account while
retaining a URL for another owner's Draft produces the existing workspace error.
Ownership is enforced; navigating to the workspace root works. Draft ownership
and navigation business behavior were left intact.

Review/merge and any broader CI/provider/PDF verification belong to the repository
owner. No deployment, push, PR, AGENT.md or WORKLOG.md publication was performed.
