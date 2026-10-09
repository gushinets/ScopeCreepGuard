"""Explicit preparation only. Drizzle remains the application migration owner."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import Connection

from alembic import command
from scope_guard.infrastructure.database.schema_verification import (
    TABLES,
    SchemaCompatibilityError,
    SchemaDifference,
    verify_baseline,
)

BASELINE = "0001_existing_drizzle_schema"


def config(connection: Connection) -> Config:
    location = Path.cwd() / "alembic.ini"
    if not location.is_file():
        raise RuntimeError("Run database tooling from the backend directory")
    result = Config(str(location))
    result.attributes.update(connection=connection, verified_operation=True)
    return result


def current_revision(connection: Connection) -> str | None:
    if connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar() is None:
        return None
    values = (
        connection.exec_driver_sql("SELECT version_num FROM public.alembic_version").scalars().all()
    )
    if values != [BASELINE]:
        raise SchemaCompatibilityError([SchemaDifference("unexpected_alembic_revision")])
    return BASELINE


def upgrade_empty(connection: Connection) -> None:
    if current_revision(connection) is not None:
        verify_baseline(connection)
        return
    objects = connection.exec_driver_sql("""
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')
        UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
        WHERE n.nspname='public' AND t.typtype='e'
    """).first()
    if objects is not None:
        raise SchemaCompatibilityError([SchemaDifference("database_not_empty")])
    connection.exec_driver_sql("SET LOCAL search_path TO public")
    command.upgrade(config(connection), BASELINE)
    verify_baseline(connection)


def adopt_baseline(connection: Connection) -> None:
    # A migration freeze is required: these locks protect existing tables but
    # cannot coordinate independent Drizzle DDL affecting standalone enum types.
    verify_baseline(connection)
    connection.exec_driver_sql(
        "LOCK TABLE " + ", ".join("public." + table for table in TABLES) + " IN SHARE MODE"
    )
    verify_baseline(connection)
    if current_revision(connection) is None:
        command.stamp(config(connection), BASELINE)
