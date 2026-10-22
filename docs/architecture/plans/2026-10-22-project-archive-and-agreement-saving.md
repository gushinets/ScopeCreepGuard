# Project archive and agreement saving

- Branch/base: continue `codex/design-onboarding`, preserving all existing local work; no push or PR.
- Scope: make archived projects available directly in History without activating their working draft; keep active Projects and Drafts archive-free. Expose explicit draft save, immutable History snapshot save, and finalization in the agreement editor in English and Russian.
- Exclusions: no project restoration, scheduled deletion, new user settings, schema changes, or changes to analysis, commercial calculations, autosave, and existing snapshots.

## Implementation

1. Inspect workflow ownership, archive behavior, editor save barriers, existing History/finalization operations, and regression fixtures.
2. Give History its own active/archived project selector and selection URL. Remove archive browsing from active Projects and the archived-project upsert. Correct deletion copy to describe archiving.
3. Reuse the existing flush, snapshot, and finalization operations from an editor action bar. Keep working saves distinct from frozen snapshots and finalization; preserve errors, retries, readiness, document content, and autosave.
4. Add focused frontend and PostgreSQL regression coverage. Run Docker checks and controlled-response browser journeys at desktop/mobile widths in both languages; capture evidence.

## Verification and handoff

Implemented on the current branch without replacing earlier changes. History owns its project selection and includes archived projects; viewing records never installs an archived working draft or changes the active project list. The agreement editor reuses the existing flush, History snapshot, and finalization operations, including repeat-finalization handling and localized feedback. No API/schema changes, restoration, or scheduled deletion were needed.

Verification: Docker build/typecheck and frontend lint/boundaries passed; frontend suite 366 passed (one unrelated Python interoperability file excluded from the Node-only image); final focused pass 59 passed; PostgreSQL regression 2 passed across compatibility/current schemas; Python Ruff passed. Both browser journeys passed in English desktop and Russian mobile, including reload, a failed finalization/retry, immutable earlier snapshots, and archived History browsing alongside an active project. Mobile History width/wrapping issues found in browser review were fixed.

Screenshots, reproduction source, API details, and verification limitations: [evidence](../evidence/2026-10-22-project-archive-and-agreement-saving/README.md). Full backend suite and real provider calls were not run. Branch remains `codex/design-onboarding`; changes are uncommitted and unstaged alongside preserved prior work. No push or PR. Owner: current task; no external follow-up assigned.
