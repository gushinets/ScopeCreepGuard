# Single onboarding walkthrough

This supersedes the duplicated guidance from the earlier design iteration.
Implementation record: [one onboarding walkthrough](../../plans/2026-10-22-single-onboarding-guide.md).

There is one shared, non-modal guide card. Its steps follow actual actions:
open a project form, save its agreed scope, submit a successful check, and review
the assessment/reply. Progress stays inside the card. The target outline and
connector show which control it belongs to. Mobile uses an adjacent normal-flow
slot. No sidebar checklist, repeated tutorial examples, static scope-help panel,
result tutorial list, Next, restart or onboarding setting remains.

| Screen | Screenshot |
| --- | --- |
| Opening guide, English | [Desktop](screenshots/single-guide-start-en-desktop.png) |
| Opening guide, Russian | [Desktop](screenshots/single-guide-start-ru-desktop.png) |
| Scope form, English | [Desktop](screenshots/single-guide-scope-en-desktop.png), [phone](screenshots/single-guide-scope-en-mobile.png) |
| Scope form, Russian | [Desktop](screenshots/single-guide-scope-ru-desktop.png), [phone](screenshots/single-guide-scope-ru-mobile.png) |
| Request step | [Phone](screenshots/single-guide-onboarding-request-mobile.png) |
| Result step | [Phone](screenshots/single-guide-onboarding-ready-mobile.png) |
| Agreement preserved | [Desktop](screenshots/single-guide-workbench-agreement-desktop.png) |
| Form after Skip | [Desktop](screenshots/single-guide-skipped-form-desktop.png) |
| Auth without tutorial | [Desktop](screenshots/login-desktop.jpg), [phone](screenshots/login-mobile.jpg) |

Verified in Docker/browser: complete action-driven journey; one card at a time;
failed form/check not advancing; keyboard start; Skip/close persistence; no
tutorial returning on reload; usable project form after Skip; desktop/mobile,
EN/RU; responsive placement stability; complete assessment and agreement workflow.
Controlled AI fixtures only. Database-backed eligibility and terminal states use
the existing implementation unchanged.

360 frontend tests passed (50 files), plus the final 30-case affected-area rerun.
One existing Python/JOSE cross-runtime test file remains excluded in the Node-only
Docker image. Build, TypeScript, lint and boundaries passed. No backend/PDF export
suite was rerun; no business logic changed. The existing JS bundle warning remains.

ROUND 2 — single-guide screenshots

Seen in one second: one card connected to the next real action.
Idea (one sentence): teach the workflow through one persistent visual pattern,
without explanatory panels competing with it.
Live thing: create a real project, check its request, then review/edit the result.
Layout words by section: start=action / scope=form / check=comparison /
result=evidence / guide=connected-card.
Scores: design 7 · usability 8 · creativity 7 · content 8 → overall 7.4.
Caps applied: the familiar document-workbench pattern caps creativity at 7;
app exceptions apply to small labels, borders and functional SVG instead of photos.
Top three problems, each with evidence and disposition:
1. Duplicate teaching blocks competed with the card (user's first attachment).
   Removed all repeated panels; `single-guide-scope-ru-desktop.png` shows one guide.
2. A centered opening card could collide with the explanatory line above its
   target. Added a safe top-aligned side candidate; the final opening screenshots
   show a clear curved connector and uncovered primary action.
3. Empty-state/form CSS could restyle a portalled inline card on phones.
   Scoped those selectors to direct children. Final desktop/mobile scope screenshots
   share the card's own typography and controls.

The auth inspector reports no failures and one desktop spacing warning. The
centered access form intentionally keeps whitespace; a replacement teaching or
marketing panel would conflict with this request. See [raw report](auth-inspection.json).
