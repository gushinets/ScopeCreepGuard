# Backend CI: onboarding schema consistency

The reported run executed 942 tests: 940 passed and two failed. Both failures were reproduced in Docker using owned disposable PostgreSQL databases.

## Causes and changes

1. The synthetic future-head fixture removed production migrations 0002–0007 but retained 0008, leaving a reference to a missing parent. It now copies only the production baseline and adds its synthetic probe. New production revisions cannot accidentally enter that test lineage.
2. Current `WORKFLOW_METADATA` loaded the 0006 catalog; importing `models.profiles` appended the onboarding columns as a side effect. The mapping therefore depended on import order and lacked the frozen server defaults. Current metadata now loads the 0008 catalog directly; the profiles module only exports table aliases. Two fresh-process regressions verify both import orders, stable columns, nullability and defaults.

No production migration history, database contents, or drift verification rules were changed. The historical baseline ORM remains separate. Two existing Ruff-format violations were also corrected without changing behavior.

## Verification

- Before changes, the two reported PostgreSQL cases both failed with the reported errors.
- After changes, the complete baseline, profile migration, schema compatibility and onboarding suites plus current/historical metadata tests passed: **40 tests**.
- Full backend/API Ruff check passed.
- Full backend/API Ruff format check passed: **379 files**.
- Type checking: both Linux and win32 mypy runs passed, **230 source files** each. They ran in an ephemeral Docker container after `uv sync --locked --all-packages --all-groups`; no host virtual environment or application container dependencies were changed.

Tests ran in Docker with disposable databases on the isolated verification PostgreSQL server. The application databases were not used as test targets. This is not a claim that the entire 944-test suite or all remaining CI stages have been rerun locally.

The feature branch has been locally rebased to satisfy the linear-history gate. Remote history remains unchanged pending the user's explicit authorization for force-with-lease.
