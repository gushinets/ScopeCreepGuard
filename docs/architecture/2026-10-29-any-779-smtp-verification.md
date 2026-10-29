# ANY-779 SMTP verification — 2026-10-29

Branch: `codex/any-779-async-smtp`. Intended PR base:
`codex/any-758-email-verification-password-reset`.
Tested HEAD: `9da7aa54d5b4961d664b6c4ef591cee7cbe7f6d9`, plus uncommitted ANY-779
source (email contracts/service/adapter, Settings, API wiring, dependency + lock,
Compose backend environment, examples, README, unit/integration checks).
No commits, pushes or Linear changes. The unrelated ANY-778 diagnosis is preserved.

Fresh checks image: `sha256:a3490dc3195515fb2d4bf5ee093a77fec1823e27032cf820152d77e797779e97`.
Revision label: `org.opencontainers.image.revision=9da7aa54d5b4961d664b6c4ef591cee7cbe7f6d9`.
Mailpit existing pinned image (not rebuilt):
`sha256:0790692be935ea4420d085694f7985b1f692ca6a8771ab0e0bd8ba75ac180498`.
Compose project: `any779-smtp-20261029`; default loopback UI port 8025.
The isolated Mailpit container is stopped; its project volume was not removed.
No database, object storage, paid LLM call or external mailbox was used.

Real EmailService → aiosmtplib → Mailpit check: PASS for all four kind/locale pairs.
Sender, recipient, subject, text, HTML, supplied URL, 24-hour wording and Message-ID
were checked via Mailpit API. SMTP CRLF is normalized when comparing bodies.
Exact reproducible commands are in README, Backend email section.

Targeted command:
`.venv/Scripts/python -m pytest backend/tests/unit/test_email.py backend/tests/unit/test_config.py -q -p no:cacheprovider`
Result: 47 passed (36 email tests).
Ruff check of backend source, API source and new tests: PASS.
Ruff format check of changed Python files: PASS.
Mypy backend/src/scope_guard + apps/api/src/scope_guard_api: PASS, 237 source files.
`git diff --check`: PASS. Dependency lock changed only for aiosmtplib 5.1.3.

The initial full backend test run was interrupted after failures/errors; it is not
a passing verification. The unit-only run had 783 passed and six Windows Temp
permission errors in test_openapi_export (2) and test_technical_operations (4).
A second sandboxed unit run exited 1 without a summary; a focused attempt reproduced
Temp permission failures even with workspace basetemp. A permitted rerun follows.
A Docker rebuild was interrupted by daemon EOF; the final rebuild and SMTP check passed.

Bounded email infrastructure verification only, not full application E2E readiness.
External SMTP/TLS is covered by deterministic flag/error tests, not external delivery.
UX, token persistence/expiry enforcement, confirmation/reset routes and auth behavior
remain for later auth tasks. No automatic retries; success means SMTP acceptance.

Final unit-only command with permitted execution:
`.venv/Scripts/python -m pytest backend/tests/unit -q -p no:cacheprovider --tb=short`
Result: 788 passed, 6 Temp permission errors. A focused retry uses a fresh
workspace basetemp, without changing the system Temp directory.
Focused retry:
`.venv/Scripts/python -m pytest backend/tests/unit/test_openapi_export.py backend/tests/unit/test_technical_operations.py -q -p no:cacheprovider --basetemp D:/Devpy/ScopeCreepGuard/.any779-permitted-temp --tb=short`
Result: 6 passed in 23.33s. Thus all collected unit tests passed across the
788-pass run and the six-test retry; no single full green run is claimed.
