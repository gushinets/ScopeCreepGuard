# Analysis workspace tabs

- Request: three result tabs — Scope, client reply, agreement — and contextual onboarding for each.
- Base/branch: current `codex/design-onboarding`, starting at `e1dd09b`; clean working tree. Continue on this feature branch and preserve unrelated work.
- Design: retain the existing typography, teal accent and shared controls. Use visible tab labels, keyboard navigation and a mobile tab row. Keep one contextual guide.

## Scope and exclusions

Move existing result content into three panels without changing analysis, pricing, languages, autosave, PDF, History or Draft semantics. Opening a tab does not generate content. A new check starts at Scope; switching tabs preserves edits. No settings, restart flow, extra instructional cards or paid model calls.

## Implementation

1. Add an accessible three-tab result workspace. Keep panels mounted, hide inactive panels, and move the existing agreement editor into its panel rather than a separate portal below the workspace.
2. Keep language selection with the client materials, estimate recovery with the agreement, and rationale/feedback with Scope.
3. Extend the single onboarding guide with tab-specific targets and concise Russian/English copy. Existing database step 3 remains the result-review phase; its current tab is presentation state. Finish only after the user acknowledges the last tip. Reloads resume this unfinished phase at Scope. Existing terminal states stay terminal; reuse the existing completion and skip API operations.
4. Add regression coverage for default selection, keyboard switching, no generation on switching, retained edits, errors and onboarding completion/skip.
5. Run Docker build, lint and frontend tests. Verify controlled AI journeys in the browser in English/Russian and desktop/mobile, including agreement preparation, autosave and PDF. Capture screenshots and record actual results here.

## Verification and handoff

Implemented three labelled, keyboard-accessible tabs. Panels stay mounted to preserve edits; the agreement editor now renders inside its tab. Client language controls remain with the reply and apply to all client materials. New checks reset to Scope; ordinary edits and language changes do not reset tab selection.

Verification: Docker build/typecheck, lint/boundaries and 381 frontend tests across 51 files passed. After simplifying completion to depend solely on the persisted state, all 15 onboarding tests, build/typecheck and lint passed again. The existing Python interoperability test is excluded from the Node-only test image. The existing bundle-size warning remains.

Browser: controlled AI journeys passed in RU/EN at 1440×1000 and 390×844. Verified full rationale, language/tone controls, no generation on switching, retained reply and commercial edits, agreement preparation, direct PDF, reload persistence, default Scope on another check, keyboard access, one guide, mobile skip on each result tab, failed analysis not advancing, delayed second-tab events staying terminal, and nonblocking onboarding endpoint failure. Screenshots and details: [evidence](../evidence/2026-10-23-analysis-tabs/README.md).

No database migration or API contract change. The existing result-review database phase covers the three guide panels; an unfinished result tour resumes at Scope after reload. Existing completed/skipped users remain excluded. No settings or restart control. Follow-up owner: current feature branch maintainer. No merge is authorized.
