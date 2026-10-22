# Compact History and explicit project restoration

- Base/branch: current `codex/design-onboarding`; preserve all local changes, no push/PR.
- User-approved change supersedes the earlier exclusion of restoration: list projects in compact rows, expand their details only on request, and restore archived projects explicitly.
- Steps: inspect archive boundaries; add owner-scoped idempotent restore through repository/service/API; replace History selector with accessible expandable project rows; preserve all checks, documents, autosave and PDF actions; add regression coverage and verify Docker/browser in Russian/English and mobile.
- No deletion worker or schema migration. Restoration clears archive state without creating or replacing any draft/check/agreement. Viewing details remains read-only.
- Verification/handoff: implemented. Docker build/typecheck, lint, targeted Ruff, 374 frontend tests and 2 PostgreSQL archive/restore regressions passed. Russian/English desktop/mobile browser journeys verified expansion, explicit restoration, reload persistence and unchanged draft/history. See [evidence and screenshots](../evidence/2026-10-22-compact-history-and-project-restore/README.md) for details and limitations. No push/PR. Owner: current task; no external follow-up assigned.
