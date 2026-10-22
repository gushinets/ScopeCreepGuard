# Restore automatic agreement persistence and direct PDF download

- Branch/base: current `codex/design-onboarding`; preserve all earlier changes. No push or PR.
- Supersedes the manual editor save/snapshot/finalize controls introduced by the earlier agreement-saving plan. User now requires automatic persistence and a direct Download PDF action below the agreement.
- Scope: retain existing PostgreSQL draft autosave and save barriers; remove normal manual save/finalize controls from editor/History; restore direct PDF rendering through the existing owned preview operation, without requiring finalization or export storage. Preserve all prior immutable History entries and finalized agreements.
- Archived projects remain archived indefinitely: expose the retained, automatically saved draft read-only within History, including documents that were edited after their last check. Never activate the archived draft in Projects/Drafts. No restoration or seven-day deletion worker.

## Steps

1. Inspect autosave, archive ownership, legacy PDF rendering, current editor/History controls, and regression coverage.
2. Replace the manual action block with shared PDF download controls. Flush the editor before downloading its current persisted document; preserve cancellation, localized errors, language checks, amounts, and all document fields.
3. Make the latest retained draft visible for archived projects in History, with direct PDF download. Keep saved check snapshots and existing durable exports unchanged.
4. Add focused frontend/PostgreSQL regression tests; build/lint/test in Docker; verify actual autosave, reload, archive/History access, and real PDF bytes in Russian/English desktop/mobile browser journeys using controlled AI responses.

## Handoff

Browser verification found that the intentional workflow boundary blocks the old `/api/change-orders/pdf` route with 426. Add the versioned `/api/v2/change-orders/pdf` alias for this existing owned, read-only preview use case; retain the old boundary, renderer, and validation. Regenerate the API contract/types. No database migration. Keep local `gpt-6-luna` configuration unchanged. Implemented and verified: Docker build/typecheck, lint, 372 frontend tests (40 affected tests rerun after the API alias), 7 API tests, 2 PostgreSQL archive tests, and Russian/English desktop/mobile browser journeys. Four real PDFs preserve all edited terms and the latest text. See [verification and screenshots](../evidence/2026-10-22-automatic-agreement-saving-and-pdf/README.md) for evidence and test-environment limitations. Current branch remains `codex/design-onboarding`, with earlier and current local changes uncommitted. No push or PR. Owner: current task; no external follow-up assigned.
