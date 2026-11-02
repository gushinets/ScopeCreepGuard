# ANY-769 — PDF preview document references

- Base: origin/main cfa3578; branch: codex/any-769-pdf-preview-draft-id.
- Workflow: ordinary branch in existing checkout; preserve stashes and local reports.
- Scope: retain optional draftId as a historical document reference, never a working v2 draft.
- Reproduce with a failing HTTP regression on Alembic head, record the exact SQL exception.
- Reuse the revision allowlist in database/legacy_boundary.py before historical document SQL; unavailable references return 404 errors.draftNotFound. Preserve malformed-ID behavior and historical snapshots. Map project ownership errors narrowly.
- Files: legacy boundary, draft persistence, technical route, current-schema integration tests; schema description/contracts only if needed.
- Verify RU/EN PDF text, owned/foreign/cross-project/missing/malformed references, read-only behavior and absence of incompatible SQL; retain historical regression. Run focused tests, lint and contract freshness.
- No LLM worker/provider calls, schema changes, frontend redesign or storage acceptance. Disposable PostgreSQL only.
- Evidence and remaining limitations: pending execution. Handoff owner: implementing agent; review via PR to main, no merge or Linear writes.

## Reproduction and implementation evidence

Tested base revision: cfa3578e8a3b598637001932519cde1dbfca7f3a plus the scoped source diff in this PR (technical route, legacy boundary, draft persistence, tests and generated documentation). No source overlays in the built image. Host tests import local workspace sources.

Before the fix, current-head HTTP regression returned 500 errors.requestFailed. A direct call to the same repository identified sqlalchemy.exc.ProgrammingError wrapping psycopg.errors.UndefinedColumn: column drafts.history_entry_id does not exist. The generated SELECT joins history_entries through the column retired by 0004.

Implementation reuses the existing legacy revision allowlist before load_owned. Unsupported references return None and the existing service produces 404 errors.draftNotFound. Malformed draft IDs retain 404; malformed project IDs retain 400 errors.requestBodyInvalid. Missing/foreign project lookup now maps ProjectError narrowly to 404 errors.projectNotFound. Database errors propagate normally. Historical queries, ownership predicates and immutable snapshots remain intact.

Current UI inspection: persistent agreement operations, archived drafts and persistent history preview submit projectId/changeOrder without draftId. Legacy change-order UI retains the optional historical reference. No frontend behavior change was needed. OpenAPI describes the reference and generated.ts was regenerated.

## Verification

- From backend: uv run --package scope-guard --group dev pytest tests/integration/test_document_current_schema.py tests/integration/test_document_workflows.py tests/api/test_python_services.py -q --tb=short: 10 passed. Current-head and baseline fixtures use isolated disposable PostgreSQL databases via existing helpers; current tests check both gated aliases, RU/EN parsed PDF text, missing/owned/foreign/cross-project/malformed references, all mapped table contents and no incompatible SELECT.
- Historical test strengthened with cross-project rejection and preview content checks after changing current terms; standalone rerun: 1 passed.
- API/unit suite: 928 passed, 9 setup errors caused by Windows shared pytest temporary-directory permissions. Re-ran test_email_worker_health.py, test_openapi_export.py and test_technical_operations.py with a task-specific --basetemp: 9 passed.
- Ruff check and format check across backend/apps/api: passed (432 files formatted). Mypy: no issues in 248 source files.
- OpenAPI export/freshness via backend/scripts/export_openapi.py; frontend scripts/api-types.mjs generation/check: passed. TypeScript via node node_modules/typescript/bin/tsc --noEmit: passed. pnpm wrapper could not fetch its pinned version; direct installed tooling succeeded.
- Documented deploy/compose.backend.yaml, isolated project scg-any769-20261102, synthetic explicit env-file: up -d --build migrate; one-shot migration gate exited 0 at 0011_password_recovery. API image freshly built: sha256:87bbcb06b10aa06abaa4b13ecc4ae7d45793c42e0cfcb51f101e0de7c94120dd; revision label cfa3578e8a3b598637001932519cde1dbfca7f3a (base plus source changes above). PostgreSQL image: sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b, no application revision label. Own PostgreSQL service stopped afterward; volume retained.
- No llm-worker started; no provider API calls. No object storage was needed. This is bounded preview/migration verification, not full application end-to-end acceptance. Remaining broad integration suite is left to CI; CI state must be reported separately.
