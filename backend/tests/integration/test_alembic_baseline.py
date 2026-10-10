import shutil
from pathlib import Path

import pytest
from alembic.config import Config
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


def test_guarded_migrate_initializes_empty_database_and_is_idempotent(disposable_url):
    from scope_guard.infrastructure.database.migrations import BASELINE, migrate

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            migrate(connection)
            migrate(connection)
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
                == BASELINE
            )
    finally:
        engine.dispose()


def test_guarded_migrate_upgrades_known_baseline_to_test_only_future_head(
    disposable_url, monkeypatch, tmp_path
):
    """A known baseline must advance through local descendants, not be rejected."""
    from scope_guard.infrastructure.database import migrations

    root = Path(__file__).resolve().parents[2]
    future_alembic = tmp_path / "alembic"
    shutil.copytree(root / "alembic", future_alembic)
    shutil.copy(
        root / "tests/fixtures/alembic_future/0002_revision_probe.py",
        future_alembic / "versions/0002_revision_probe.py",
    )
    future_ini = tmp_path / "alembic.ini"
    shutil.copy(root / "alembic.ini", future_ini)

    def future_config(connection):
        result = Config(str(future_ini))
        result.attributes.update(connection=connection, verified_operation=True)
        return result

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            migrations.migrate(connection)
            assert migrations.current_revision(connection) == migrations.BASELINE
        monkeypatch.setattr(migrations, "config", future_config)
        with engine.begin() as connection:
            migrations.migrate(connection)
            assert migrations.current_revision(connection) == "0002_revision_probe"
            assert connection.exec_driver_sql(
                "SELECT to_regclass('public.revision_probe')"
            ).scalar()
            migrations.migrate(connection)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("revisions", "reason"),
    [
        (["not_a_local_revision"], "unknown_alembic_revision"),
        (["0001 invalid"], "malformed_alembic_revision"),
        (["0001_existing_drizzle_schema", "not_a_local_revision"], "multiple_alembic_revisions"),
        ([], "missing_alembic_revision"),
    ],
)
def test_guarded_migrate_rejects_invalid_alembic_version_state(disposable_url, revisions, reason):
    """Invalid version ledgers must fail before the guarded runner upgrades anything."""
    from scope_guard.infrastructure.database.migrations import migrate
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE public.alembic_version (version_num varchar(32) NOT NULL)"
            )
            for revision in revisions:
                connection.exec_driver_sql(
                    "INSERT INTO public.alembic_version(version_num) VALUES (%s)", (revision,)
                )
        with engine.begin() as connection:
            with pytest.raises(SchemaCompatibilityError, match=reason):
                migrate(connection)
            assert connection.exec_driver_sql(
                "SELECT version_num FROM public.alembic_version"
            ).all() == [(revision,) for revision in revisions]
    finally:
        engine.dispose()


def test_guarded_migrate_requires_explicit_legacy_adoption(disposable_url):
    from scope_guard.infrastructure.database.migrations import BASELINE, migrate
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            with pytest.raises(SchemaCompatibilityError, match="legacy_adoption_required"):
                migrate(connection)
            assert (
                connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar()
                is None
            )
        with engine.begin() as connection:
            migrate(connection, adopt_legacy=True)
            migrate(connection)
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
                == BASELINE
            )
    finally:
        engine.dispose()


def test_guarded_migrate_rejects_unknown_non_public_schema(disposable_url):
    from scope_guard.infrastructure.database.migrations import migrate
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE SCHEMA unknown")
            connection.exec_driver_sql("CREATE TABLE unknown.data(id integer)")
        with engine.begin() as connection:
            with pytest.raises(SchemaCompatibilityError, match="legacy_adoption_required"):
                migrate(connection)
            assert (
                connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar()
                is None
            )
    finally:
        engine.dispose()


def test_guarded_migrate_rejects_legacy_ledger_hash_drift(disposable_url):
    from scope_guard.infrastructure.database.migrations import migrate
    from scope_guard.infrastructure.database.schema_verification import SchemaCompatibilityError

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE drizzle.__drizzle_migrations SET hash=repeat('0',64) WHERE id=1"
            )
        with engine.begin() as connection:
            with pytest.raises(SchemaCompatibilityError, match="legacy_ledger_provenance"):
                migrate(connection, adopt_legacy=True)
            assert (
                connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar()
                is None
            )
    finally:
        engine.dispose()
