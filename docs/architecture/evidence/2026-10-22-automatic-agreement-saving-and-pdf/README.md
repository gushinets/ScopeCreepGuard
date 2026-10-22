# Automatic agreement saving and PDF downloads

Verified on 2026-10-22, branch `codex/design-onboarding`. All earlier local work was preserved. No commits, pushes, or PRs were created.

## Result

The manual save/snapshot/finalize block has been removed from the editor. The existing PostgreSQL autosave remains authoritative. Download PDF sits below the agreement and flushes pending edits before rendering the saved document. Failed persistence prevents downloading an outdated version and leaves edits available for retry.

Archived projects remain absent from active Projects and Drafts. History reads their retained working draft without installing it in the editor or reactivating the project. The latest saved agreement remains viewable and downloadable, including edits made after the last check. Existing immutable checks and finalized agreements/exports remain intact. No restoration or scheduled deletion was added.

## Database and API

No database changes for this task. Added authenticated `POST /api/v2/change-orders/pdf`, an alias to the existing owned, read-only document preview/rendering operation. The legacy route remains blocked in workflow-v2 mode. Existing renderer, validation, owner isolation and private/no-store headers are reused; no finalization, AI call or object storage is required. OpenAPI and TypeScript types were regenerated.

## Verification

- Docker frontend build/typecheck passed; ESLint and dependency boundaries passed (99 modules).
- Frontend suite: 372 tests passed across 50 files. The existing Python/JOSE interoperability test was excluded because the Node test image does not contain Python/uv. After the versioned PDF route change, all 40 affected editor/History tests passed again.
- Docker API tests: 7 passed, including real PDF output on legacy and versioned paths, private caching and the retained legacy-route boundary.
- PostgreSQL archive regression: 2 passed (migration 0004 and current head), preserving checks/agreements, owner isolation and read-only PDF access after archive.
- Targeted Ruff checks and OpenAPI contract check passed. The initial API-test attempt used the global interpreter, whose isolated subprocess lacked renderer dependencies; rerunning with the application's virtual environment passed all 7 tests.
- Browser: both English and Russian, desktop 1440x1000 and mobile 390x844. Created a project, ran a controlled check, prepared and edited an agreement, verified automatic persistence/reload, then downloaded immediately after a final edit. Archived the project, checked active Projects/Drafts were empty, opened History, downloaded the retained agreement, and reloaded History. Old check snapshots were unchanged, and History never reactivated the project. Neither mobile layout overflowed horizontally.
- Four real downloaded PDFs parsed successfully. Their extracted text contains the last edit, 9.5 hours, 777.25 EUR, provider/client names and additional terms. Editor and archived copies have matching document text in each language, including Cyrillic.
- Main local app at `http://localhost:3000` serves the verified build; its PDF route requires authentication. Backend remains `gpt-6-luna`.

Browser journeys used real APIs/PostgreSQL with deterministic AI responses on the isolated Docker verification app at port 3100. No paid provider calls. The normal application at port 3000 retains its real worker/model configuration. Full backend CI and a live provider run were not performed for this change; existing durable object-storage exports were preserved and covered by UI regressions, not re-provisioned.

## Screenshots and sample files

All screenshots and PDFs contain synthetic verification data.

- [Russian editor, desktop](automatic-editor-ru-desktop.png)
- [Russian editor, mobile](automatic-editor-ru-mobile.png)
- [Russian archived project in History](automatic-history-ru-desktop.png)
- [Russian History, mobile](automatic-history-ru-mobile.png)
- [English editor, desktop](automatic-editor-en-desktop.png)
- [English editor, mobile](automatic-editor-en-mobile.png)
- [English History, desktop](automatic-history-en-desktop.png)
- [English History, mobile](automatic-history-en-mobile.png)
- [Russian PDF](automatic-agreement-ru.pdf), [archived Russian PDF](automatic-archived-ru.pdf)
- [English PDF](automatic-agreement-en.pdf), [archived English PDF](automatic-archived-en.pdf)

`browser-verification.js` records the complete journey. `verify-pdf-content.py` records the content assertions; its original Docker paths refer to ignored local output files.
