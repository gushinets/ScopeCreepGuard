# One onboarding walkthrough

Issue: remove duplicated education and rebuild the guide using the user's second
attached example. Branch/base: existing codex/design-onboarding, origin/main
f3e34de; preserve all uncommitted work. No new checkout, push or PR.

The first attached image identifies the static scope-help panel to remove. The
second establishes the guide's visual anatomy: one card, step count, progress
dots, close action, target outline and connector. Its example Next button does
not override the earlier action-driven requirement; real actions advance steps.
Retain the current application visual system rather than copy its purple palette.

Scope: one centrally mounted guide for the first-use journey. Remove the sidebar
task trail, start-page tutorial/example, duplicated form-help panel and result
tutorial list. Keep functional labels, validation, rationale, replies, language
controls and agreement behavior. Keep concise normal empty states. Remove the
repeated auth example and rebalance that layout. One initial create action per
empty screen; guide attaches to it. No settings/restart or backend/state changes.

Steps:
1. Replace per-screen tip instances with empty anchor slots and one guide host.
   Use a white bordered card with progress, safe placement and connector.
2. Remove the duplicated educational UI and simplify affected layouts/copy in
   English and Russian. Preserve the existing real-action event/state service.
3. Add meaningful tests for one card, action transitions, dismissal, placement
   stability and connector bounds. Run Docker lint/build/tests.
4. Verify the actual journey, Skip/reload, no duplicated panels, desktop/mobile
   and EN/RU in a browser using controlled AI. Capture screenshots and results.

Owner: current chat. Preserve the previous Projects layout-shift fix: no passive
inline-to-floating promotion. Mobile/limited space uses an adjacent anchor slot;
empty slots do not allocate a hidden tutorial panel. Guidance cannot cover inputs
or trap focus. No model calls or business logic changes are needed.

## Implementation and verification

One OnboardingGuide is mounted in the workspace layout. Pages expose only empty
OnboardingSlots beside real controls; the guide renders into one safe destination.
The card has a localized step count, four progress dots, close action, target
outline and curved SVG connector. Narrow screens use the same card in an adjacent
slot; no floating card covers a field. Only the final card has a Got it action.

Removed the sidebar checklist, opening task list, repeated scope/request example
(including auth), the scope-reference panel from the supplied first image, and
the result tutorial list. Empty Projects has one create action. Project forms
remain bounded/readable without a second instructional column. Normal labels,
upload constraints, validation, saved-scope rationale and business messages remain.
Retired instructional copy was removed from both catalogs. There are no onboarding
settings, restart controls, Next buttons, new database fields or API changes.

Docker verification: 360 frontend tests passed in 50 files; the same existing
Python/JOSE cross-runtime interop file remains excluded because the Node-only test
image lacks Python/uv. Final focused rerun: 30 passed. Production build/TypeScript,
ESLint and dependency boundaries (96 modules), and Git whitespace checks passed.
The existing >500KB bundle warning remains (615KB before gzip).

Browser: complete keyboard-started first-use journey, invalid form and failed
check not advancing, one card through actual form/save/check/result actions,
agreement preparation, and completion persistence passed with controlled AI.
No paid provider calls. The card's X immediately dismisses, saves skipped state,
and stays absent after reload; the project form remains usable without any tutorial.
EN/RU opening cards and clean scope forms were inspected on desktop and phone.
Russian Projects resizing through 1440/1280/1100/768/390px and back was stable over
75 sampled frames per viewport, without horizontal overflow. The prior passive
inline-to-floating layout-shift regression remains covered.

Static UI scan: 0 failures; six warnings are existing mono theme definitions,
loading skeleton pulses and the legitimate floating-card shadow. The unmodified
auth inspector has 0 failures and one desktop empty-space warning, retained as an
intentional centered access form after removing the duplicate instructional panel.

Screenshots and verification notes:
[Single walkthrough evidence](../evidence/2026-10-22-single-onboarding-guide/README.md).
No backend business logic was changed or retested. Earlier uncommitted work is
preserved on codex/design-onboarding. No commit, push, PR or deployment.
