import pytest
from integration.support import replay_drizzle
from sqlalchemy import create_engine

pytestmark = pytest.mark.integration


def test_current_drizzle_matches_frozen_manifest(disposable_url):
    from scope_guard.infrastructure.database.schema_verification import verify_baseline

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            verify_baseline(connection)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "ddl",
    [
        "ALTER TABLE projects DROP COLUMN client",
        "ALTER TABLE projects ALTER COLUMN hourly_rate TYPE numeric(15,3)",
        "ALTER TABLE projects ALTER COLUMN scope DROP NOT NULL",
        "ALTER TABLE drafts ALTER COLUMN status SET DEFAULT 'other'",
        "DROP INDEX drafts_project_created_at_idx",
        "ALTER TYPE currency ADD VALUE 'GBP'",
        "ALTER TABLE projects DROP CONSTRAINT "
        "projects_commercial_terms_consistent; ALTER TABLE projects ADD "
        "CONSTRAINT projects_commercial_terms_consistent CHECK (true)",
        "ALTER TABLE evaluation_cases DROP CONSTRAINT "
        "evaluation_cases_history_entry_id_history_entries_id_fk; ALTER TABLE "
        "evaluation_cases ADD CONSTRAINT "
        "evaluation_cases_history_entry_id_history_entries_id_fk FOREIGN "
        "KEY(history_entry_id) REFERENCES history_entries(id) ON DELETE SET "
        "NULL",
        "ALTER TABLE drafts ADD COLUMN unexpected text",
        "DROP TABLE evaluation_cases",
        "ALTER TABLE drafts ENABLE ROW LEVEL SECURITY",
    ],
)
def test_schema_drift_rejects_adoption_without_ledger_changes(disposable_url, ddl):
    from scope_guard.infrastructure.database.migrations import adopt_baseline
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(ddl)
        with engine.begin() as connection:
            with pytest.raises(SchemaCompatibilityError):
                adopt_baseline(connection)
            assert (
                connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar()
                is None
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM drizzle.__drizzle_migrations"
                ).scalar()
                == 7
            )
    finally:
        engine.dispose()
