# Compact History and project restoration

Branch: `codex/design-onboarding`. Prior local changes preserved; no commit, push or PR.

History now starts with compact project rows showing the name and abbreviated scope/client. The row is a keyboard-accessible expansion button; details, checks, agreements and PDF actions appear only after expansion. Archived rows have a separate Restore button, with loading/error states. Mobile rows retain one-line summaries and truncate long names; full content remains accessible in the expanded view.

Added authenticated `POST /api/v2/projects/{identifier}/restore`, routed through the existing workflow service/repository. An owned, locked project has its archive timestamp cleared. Repeated restores are safe. Draft contents/revision, check snapshots and agreement snapshots remain unchanged. No database migration or deletion worker. API contract and frontend types regenerated. Viewing details never restores a project or installs its draft in the active editor.

Verification through Docker: build/typecheck, frontend lint/boundaries, targeted Python Ruff passed. Frontend: 374 tests in 50 files passed, including 11 History tests. PostgreSQL: 2 archive/restore regressions passed on migration 0004 and head, covering repeat restore, foreign-owner rejection and unchanged drafts/checks/agreements. The existing Python/JOSE frontend interoperability test remains excluded from the Node-only image; full backend CI was not run.

Real browser journeys passed in Russian and English at desktop 1440x1000 and mobile 390x844: collapsed list, explicit expansion, no restoration on view, restore, unchanged draft/history, repeated restore and persistence after reload. Final mobile screenshots were visually inspected after fixing long-text wrapping. Synthetic accounts on the isolated Docker verification stack, no AI/provider calls. The same frontend build is installed on the normal local app at port 3000.

- [Russian desktop list](compact-history-ru-desktop.png)
- [Russian mobile list](compact-history-ru-mobile.png)
- [Russian expanded project](compact-details-ru.png)
- [English desktop list](compact-history-en-desktop.png)
- [English mobile list](compact-history-en-mobile.png)
- [English expanded project](compact-details-en.png)

Reproduction: `browser-verification.js` uses the synthetic accounts prepared by the preceding PDF verification journey and real API/DB calls. It restores then rearchives only those synthetic projects.
