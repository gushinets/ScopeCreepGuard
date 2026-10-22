# Project archive and agreement editor verification

Verified on `codex/design-onboarding` on 2026-10-22. Existing design/onboarding changes were preserved. All accounts, projects, and commercial terms below are synthetic verification data.

## Browser journeys

The Docker application at localhost:3100 used real authentication, API operations, PostgreSQL persistence, and the existing controlled-response worker. No paid model calls were made. [Browser journey source](browser-journeys.js) runs through Playwright CLI `run-code --filename` with the local isolated stack running.

- Created a project, ran a check, and prepared its agreement through the interface.
- Edited description, provider/client names, additional terms, hours (9.5), amount (777.25), and currency (EUR). Saved the working draft in the editor, reloaded, and verified the values persisted.
- Saved a History snapshot from the editor without leaving the page. Edited the description again, simulated a failed finalization, and verified the editor retained its contents. Retried successfully from the editor. Verified the finalized agreement contains the latest description and the manual commercial terms, and an earlier History snapshot remains byte-for-byte unchanged.
- Archived the project using the confirmation dialog. Verified it disappears from active Projects and Drafts while History retains its saved checks and agreement.
- Created a separate active project, selected the archived project directly in History, opened its agreement's saved check, and reloaded. History selection persists in `historyProject`; the active project remains active and the archived project is never reinserted.
- Verified archive persistence after another sign-in. Checked English desktop (1440×1000) and Russian mobile (390×844), including no horizontal overflow in the editor or History.
- Browser review caught and resolved History's unconstrained mobile column, long agreement reference wrapping, and an overly long Russian PDF action label. Selection now keeps the History screen mounted and preserves selector focus.

Final successful browser fixture: project `2303beb3-41ec-4987-ad00-bac0b50642ca`, agreement `CO-20261022-F644FF9B2CFE48BFB846D8E62F28DC17`.

## Screenshots

- [Agreement editor, English desktop](ux-agreement-editor-en-desktop.png)
- [Agreement editor actions, Russian mobile](ux-agreement-editor-ru-mobile.png)
- [Archive confirmation](ux-archive-confirmation-en.png)
- [Archived History and agreement, English desktop](ux-archived-history-en-desktop.png)
- [Archived History and agreement, Russian mobile](ux-archived-history-ru-mobile.png)
- [History project selector, English desktop](history-selector-en-desktop.png)
- [History project selector, Russian mobile](history-selector-ru-mobile.png)

A separate browser check confirmed that selecting the archived project keeps keyboard focus on the selector. History's breadcrumb no longer displays the separate active draft's project name; the archived selection is identified by the History selector itself. Final captures were refreshed after this refinement.

## Automated checks

All application checks ran in Docker using the repository's frontend dependencies and backend runtime, with bounded worker counts.

- Frontend suite: **366 passed, 50 files**. The Node-only container excludes the unrelated Python/JOSE interoperability test (`src/test/draft-proof-interop.test.ts`), which needs a Python/uv runtime.
- Final focused frontend pass: **59 passed** across persistent-store, persistent-navigation, and persistent-history tests. Includes editor save barriers, failed snapshot handling, repeat finalization, archived History without draft activation, retained agreement/download controls in both languages, and archive-list failure isolation.
- PostgreSQL regression: **2 passed**, covering `0004_workflow_retire` compatibility and the current migration head. Covers repeated archiving, preservation of two snapshots and a finalized agreement, active/archived filtering, read isolation, and owner isolation.
- Docker production build/typecheck passed. Frontend lint and dependency boundaries passed (97 modules). Python Ruff passed for the changed integration tests. Vite retains its existing large-chunk warning.

The PostgreSQL check invokes `test_completed_check_archive_and_agreement_are_independent` from the repository test module with the existing disposable-database harness in ignored `output/onboarding/`. It creates unique databases on the isolated Docker PostgreSQL service and drops only those databases afterward. The normal repository fixture remains unchanged.

## API, database, and limits

No database migration, API endpoint, or backend business rule changed for these fixes. The interface reuses `DELETE /api/v2/projects/{id}` (archive), `GET /api/v2/projects?archived=true`, the existing draft PUT/autosave barrier, `POST /api/v2/drafts/{id}/history`, and existing History agreement list/finalization operations. Existing ready exports remain downloadable; archived projects retain the backend's restriction on preparing new exports.

No restoration or scheduled deletion was added. The full backend suite and real external model/provider calls were outside this focused verification. No push, PR, commit, or staging was performed; the worktree remains intentionally dirty with earlier work and these changes. Final Git status: `codex/design-onboarding`, 48 modified tracked paths and 17 untracked entries/directories; staging is empty. `git diff --check` passed.
