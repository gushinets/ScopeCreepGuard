# Three-tab analysis workspace

Synthetic accounts and controlled provider responses, Docker verification stack at port 3100. No paid model calls. The normal local application remains at port 3000 with GPT-6 Luna.

## Verified journeys

- English and Russian: create a project, run a check, open Scope by default, review the full rationale, citations and estimate.
- Switch to Client reply, edit the message, retain language and tone controls; switch to Agreement without a generation request.
- Prepare the agreement explicitly, edit the description and price, switch away and back without losing either reply or commercial terms.
- Download PDF directly from the agreement editor; reload and verify the saved price. Existing backend operations and History behavior are unchanged.
- Run another check from a different tab and verify Scope opens first.
- Desktop 1440×1000 and mobile 390×844: all three panels, no horizontal page overflow; arrow keys switch tabs and move focus to the selected tab.
- One contextual guide follows the selected tab. Completion is acknowledged on the final guide and survives reload and sign-in from a fresh browser context.
- Mobile: skipping from Scope, Client reply and Agreement dismisses the guide immediately and persists in PostgreSQL. A delayed event from a second tab cannot reactivate it; both tabs stay dismissed after reload.
- An injected analysis failure leaves the request step incomplete. An unavailable onboarding endpoint leaves the reply editor usable.

## Automated checks

- Docker production build and type checking passed; existing warning about a JavaScript chunk larger than 500 kB remains.
- Docker lint and feature-boundary checks passed (100 modules).
- Frontend suite: 381 tests passed across 51 files. The pre-existing Python interop test is excluded in this Node-only test image because Python/uv are unavailable.
- After removing the obsolete extra final-tip state, all 15 onboarding tests passed again, along with build/type checking and lint.

## Screenshots

- [Scope and rationale, Russian](tabs-ru-scope.png)
- [Client reply and language controls, Russian](tabs-ru-reply.png)
- [Agreement guide, Russian](tabs-ru-agreement-tip.png)
- [Agreement preview and PDF download](tabs-ru-agreement-editor.png)
- [Scope, English](tabs-en-scope.png)
- [Client reply, English](tabs-en-reply.png)
- [Client reply on mobile](tabs-ru-mobile-reply.png)
- [Agreement guide on mobile](tour-mobile-ru-agreement.png)

## Persistence model and limits

No schema or API contract changes. Database step 3 now covers reviewing the result tabs; `result_viewed` completes that phase after acknowledgement. The selected result tab is presentation state. An unfinished tour resumes at Scope after reload; completed/skipped users are not enrolled again. No onboarding settings or restart action were added.
