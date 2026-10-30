"""Release migration invariants against exclusively owned PostgreSQL databases."""

import pytest
from sqlalchemy import create_engine

from scope_guard.database.migrations import current_head, current_revision, migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration


def test_previous_release_upgrade_preserves_rows_and_refuses_downgrade(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.begin() as connection:
            migrate(connection, target="0007_nonblocking_llm")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            connection.exec_driver_sql(
                "INSERT INTO users(email,password_hash) VALUES ('upgrade@example.test','synthetic')"
            )
            connection.exec_driver_sql(
                "INSERT INTO projects(user_id,name,industry,scope,updated_at) "
                "SELECT id,'Preserved','Development','original scope',now() FROM users"
            )
            connection.exec_driver_sql(
                "INSERT INTO drafts(project_id,draft_document,request_text,"
                "analysis_is_stale,revision) "
                "SELECT id,'{}','preserved request',true,1 FROM projects"
            )
            connection.exec_driver_sql(
                "INSERT INTO history_entries(project_id,date,request,verdict,summary,"
                "check_snapshot,schema_version,source_kind) SELECT id,'2026-10-01',"
                "'preserved','in_scope','original','{}',1,'legacy_unverified' FROM projects"
            )
            before = {
                table: connection.exec_driver_sql(f"SELECT to_jsonb(t) FROM {table} t").all()
                for table in ("users", "projects", "drafts", "history_entries")
            }
        with engine.begin() as connection:
            migrate(connection, target="head")
            assert current_revision(connection) == current_head(connection)
            for table, expected in before.items():
                if table == "users":
                    # 0009 adds explicit legacy defaults without changing old fields.
                    # Compare the whole row: unexpected additions or data changes fail.
                    expected = [
                        (
                            {
                                **row,
                                "session_version": 0,
                                "email_verified_at": None,
                                "email_verification_required": False,
                            },
                        )
                        for (row,) in expected
                    ]
                assert (
                    connection.exec_driver_sql(f"SELECT to_jsonb(t) FROM {table} t").all()
                    == expected
                )
        with engine.begin() as connection:
            with pytest.raises(ValueError, match="migration_downgrade_refused"):
                migrate(connection, target="0007_nonblocking_llm")
        with engine.begin() as connection:
            migrate(connection, target="head")
    finally:
        engine.dispose()


def test_database_lock_timeout_is_bounded_and_retryable(disposable_url, monkeypatch, caplog):
    engine = create_engine(normalize_url(disposable_url))
    monkeypatch.setenv("SCOPE_GUARD_MIGRATION_LOCK_TIMEOUT_SECONDS", "0.25")
    try:
        from scope_guard.database.migrations import MIGRATION_LOCK_ID

        with engine.begin() as holder:
            holder.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
            with engine.begin() as connection:
                with pytest.raises(TimeoutError, match="migration_lock_timeout"):
                    migrate(connection, target="head")
        with engine.begin() as connection:
            migrate(connection, target="head")
        assert "migration_lock_timeout" in caplog.text
    finally:
        engine.dispose()
