import pytest
from integration.support import replay_drizzle, rows
from sqlalchemy import create_engine

pytestmark = pytest.mark.integration


def test_empty_upgrade_matches_drizzle_and_metadata(disposable_url, postgres_server):
    from scope_guard.infrastructure.database.migrations import upgrade_empty
    from scope_guard.infrastructure.database.models import Base
    from scope_guard.infrastructure.database.schema_verification import (
        inspect_schema,
        verify_baseline,
    )

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            upgrade_empty(connection)
            verify_baseline(connection)
            expected = inspect_schema(connection)
            upgrade_empty(connection)
        with postgres_server.database() as metadata_url:
            metadata_engine = create_engine(
                metadata_url.replace("postgresql://", "postgresql+psycopg://")
            )
            try:
                with metadata_engine.begin() as connection:
                    Base.metadata.create_all(connection)
                    assert inspect_schema(connection) == expected
            finally:
                metadata_engine.dispose()
    finally:
        engine.dispose()


def test_populated_adoption_preserves_every_row_and_old_ledger(disposable_url):
    from scope_guard.infrastructure.database.migrations import adopt_baseline

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO users(email,password_hash) VALUES "
                "('one@test','bcrypt-fixture'),('two@test','other')"
            )
            connection.exec_driver_sql(
                "INSERT INTO projects(user_id,name,industry,scope) SELECT id,'旧 "
                "проект','Development','Original scope' FROM users"
            )
            connection.exec_driver_sql(
                "INSERT INTO history_entries(project_id,date,request,verdict,summary) "
                "SELECT id,'2026-10-09','Extra','out_of_scope','Extra' FROM projects"
            )
            connection.exec_driver_sql(
                "INSERT INTO "
                "drafts(project_id,history_entry_id,idempotency_key,analysis_snapshot,"
                "draft_document,locale,client_material_language) "
                "SELECT "
                'project_id,id,gen_random_uuid(),\'{"summary":"Русский"}\',\'{"version":1}\', '
                "'en','es' FROM history_entries"
            )
            connection.exec_driver_sql(
                "INSERT INTO "
                "evaluation_cases(user_id,history_entry_id,scope,request,ai_verdict,"
                "ai_reasoning,accuracy,industry) "
                "SELECT "
                "p.user_id,h.id,'Scope','Extra','out_of_scope','Reason','debatable','Development' "
                "FROM history_entries h JOIN projects p ON p.id=h.project_id"
            )
            connection.exec_driver_sql(
                "INSERT INTO "
                "evaluation_cases(user_id,scope,request,ai_verdict,ai_reasoning,accuracy,industry) "
                "SELECT id,'Scope','Unlinked','in_scope','Reason','debatable','Design' "
                "FROM users LIMIT 1"
            )
            before = rows(connection)
            connection.exec_driver_sql(
                "INSERT INTO projects(user_id,name,industry,scope,start_date,pricing_model,"
                "currency,hourly_rate,fixed_price) SELECT id,'Hourly','Development','Scope',"
                "'2026-01-01','hourly','USD',125.10,NULL FROM users LIMIT 1"
            )
            connection.exec_driver_sql(
                "INSERT INTO projects(user_id,name,industry,scope,start_date,pricing_model,"
                "currency,hourly_rate,fixed_price) SELECT id,'Fixed','Design','Scope',"
                "'2026-01-01','fixed','EUR',NULL,999999999999.99 FROM users LIMIT 1"
            )
            before = rows(connection)
            ledger = connection.exec_driver_sql(
                "SELECT * FROM drizzle.__drizzle_migrations ORDER BY id"
            ).all()
            adopt_baseline(connection)
            adopt_baseline(connection)
            assert rows(connection) == before
            assert (
                connection.exec_driver_sql(
                    "SELECT * FROM drizzle.__drizzle_migrations ORDER BY id"
                ).all()
                == ledger
            )
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
                == "0001_existing_drizzle_schema"
            )
    finally:
        engine.dispose()


def test_partial_schema_cannot_be_upgraded(disposable_url):
    from scope_guard.infrastructure.database.migrations import upgrade_empty
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE users(id uuid PRIMARY KEY)")
            with pytest.raises(SchemaCompatibilityError):
                upgrade_empty(connection)
            assert (
                connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar()
                is None
            )
    finally:
        engine.dispose()
