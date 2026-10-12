import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection

from alembic import command
from scope_guard.database.schema_verification import (
    TABLES,
    SchemaCompatibilityError,
    SchemaDifference,
    verify_baseline,
    verify_revision_schema,
)

"""Guarded Alembic migration ownership for empty and legacy databases."""


BASELINE = "0001_existing_drizzle_schema"
MIGRATION_LOCK_ID = 642_000_001
LEGACY_PROVENANCE = (
    (
        1786610877676,
        {
            "59e4d5764767c3dac239fa41fb156dd6ba452028be515393595b64d4a31565c9",
            "6d22bbd637c3d7ff958db9354e50555504768b5ab6344664ca849f93ae608e79",
        },
    ),
    (
        1787153535821,
        {
            "a07ed1c58e887f0ce7b516e8d72bba374fe87e8ee7bde766ca557723e6d651c2",
            "ff6c1ac9d18adf8677542b373f2b32f2a54e21cb6226d935e2aa6421267acc90",
        },
    ),
    (
        1791195354928,
        {
            "f5d6fee8e31f704c563d92e8755cbc1cbbd3e9e21df3525280d1d4842e17a965",
            "dda924ea0a19e3c524516ac284aede34c87b2f2b402cb3965172b0a2e95db82f",
        },
    ),
    (
        1791197160627,
        {
            "86c6e1d429cb26e5336fc037b861acb21c9ca8200b8682c8b6e16f3cdca0d441",
            "3065ef90acf41f77e34c8788ba1b2ca4621d064a68cb92ae5f77519b8034db5c",
        },
    ),
    (
        1791307103321,
        {
            "798df6fcb8c878bcacdf44946cc99421d8e9cc8c04f1c1930f4f3b198053de2e",
            "b5518f3bf5226e178f697201b7e464633ff95b52917ad6a8ad1913e511eead5f",
        },
    ),
    (1791364150264, {"dbb3c37d01ddfe95bbd27a5ddb9f7ab328b3ff08523b57a68cbaa70eff7da6a6"}),
    (
        1791387755044,
        {
            "59cac875d1bae08caf3fa14c18e5211cbe411e9e346ba0e41693283220d3ca4f",
            "e7b9454e8e7a0ae1d808da0e57fb6ef6a349ecda92d3f2babfdac629845af5b1",
        },
    ),
)
REVISION_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def config(connection: Connection) -> Config:
    location = Path.cwd() / "alembic.ini"
    if not location.is_file():
        raise RuntimeError("Run database tooling from the backend directory")
    result = Config(str(location))
    result.attributes.update(connection=connection, verified_operation=True)
    return result


def _lineage(connection: Connection) -> tuple[Config, set[str], str]:
    migration_config = config(connection)
    scripts = ScriptDirectory.from_config(migration_config)
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise SchemaCompatibilityError([SchemaDifference("invalid_alembic_lineage")])
    return migration_config, {revision.revision for revision in scripts.walk_revisions()}, heads[0]


def current_revision(connection: Connection) -> str | None:
    if connection.exec_driver_sql("SELECT to_regclass('public.alembic_version')").scalar() is None:
        return None
    columns = connection.exec_driver_sql("""
        SELECT column_name, data_type, is_nullable FROM information_schema.columns
        WHERE table_schema='public' AND table_name='alembic_version' ORDER BY ordinal_position
    """).all()
    if columns != [("version_num", "character varying", "NO")]:
        raise SchemaCompatibilityError([SchemaDifference("malformed_alembic_revision")])
    values = (
        connection.exec_driver_sql("SELECT version_num FROM public.alembic_version").scalars().all()
    )
    if not values:
        raise SchemaCompatibilityError([SchemaDifference("missing_alembic_revision")])
    if len(values) != 1:
        raise SchemaCompatibilityError([SchemaDifference("multiple_alembic_revisions")])
    revision = values[0]
    if not revision or not REVISION_PATTERN.fullmatch(revision):
        raise SchemaCompatibilityError([SchemaDifference("malformed_alembic_revision")])
    _, known_revisions, _ = _lineage(connection)
    if revision not in known_revisions:
        raise SchemaCompatibilityError([SchemaDifference("unknown_alembic_revision")])
    return revision


def current_head(connection: Connection) -> str:
    """Return the single configured Alembic head for the guarded lineage."""
    _, _, head = _lineage(connection)
    return head


def upgrade_empty(connection: Connection) -> None:
    revision = current_revision(connection)
    if revision is not None:
        head = current_head(connection)
        verify_revision_schema(connection, revision=revision, head=head)
        command.upgrade(config(connection), "head")
        verify_revision_schema(connection, revision=current_revision(connection), head=head)
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
    command.upgrade(config(connection), "head")
    verify_revision_schema(
        connection, revision=current_revision(connection), head=current_head(connection)
    )


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


def _has_database_objects(connection: Connection) -> bool:
    return (
        connection.exec_driver_sql("""
            SELECT 1 FROM pg_namespace n
            WHERE n.nspname NOT IN ('public', 'information_schema')
              AND left(n.nspname, 3) <> 'pg_'
            UNION ALL SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f','c','i')
            UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
            WHERE n.nspname='public' AND t.typtype <> 'p'
            UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_operator o JOIN pg_namespace n ON n.oid=o.oprnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_collation c JOIN pg_namespace n ON n.oid=c.collnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_conversion c JOIN pg_namespace n ON n.oid=c.connamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_opclass o JOIN pg_namespace n ON n.oid=o.opcnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_opfamily o JOIN pg_namespace n ON n.oid=o.opfnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_ts_config c JOIN pg_namespace n ON n.oid=c.cfgnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_ts_dict d JOIN pg_namespace n ON n.oid=d.dictnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_ts_parser p JOIN pg_namespace n ON n.oid=p.prsnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_ts_template t JOIN pg_namespace n ON n.oid=t.tmplnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            WHERE n.nspname='public'
            UNION ALL SELECT 1 FROM pg_foreign_data_wrapper
            UNION ALL SELECT 1 FROM pg_foreign_server
            UNION ALL SELECT 1 FROM pg_event_trigger
            UNION ALL SELECT 1 FROM pg_publication
            UNION ALL SELECT 1 FROM pg_subscription
        """).first()
        is not None
    )


def verify_legacy_ledger(connection: Connection) -> None:
    ledger = connection.exec_driver_sql(
        "SELECT to_regclass('drizzle.__drizzle_migrations')"
    ).scalar()
    if ledger is None:
        raise SchemaCompatibilityError([SchemaDifference("legacy_ledger_missing")])
    columns = connection.exec_driver_sql("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema='drizzle' AND table_name='__drizzle_migrations'
        ORDER BY ordinal_position
    """).all()
    if columns != [("id", "integer"), ("hash", "text"), ("created_at", "bigint")]:
        raise SchemaCompatibilityError([SchemaDifference("legacy_ledger_shape")])
    rows = connection.exec_driver_sql(
        "SELECT created_at, hash FROM drizzle.__drizzle_migrations ORDER BY id"
    ).all()
    if len(rows) != len(LEGACY_PROVENANCE) or any(
        created_at != expected_at or digest not in expected_hashes
        for (created_at, digest), (expected_at, expected_hashes) in zip(
            rows, LEGACY_PROVENANCE, strict=True
        )
    ):
        raise SchemaCompatibilityError([SchemaDifference("legacy_ledger_provenance")])


def migrate(connection: Connection, *, adopt_legacy: bool = False) -> None:
    """Upgrade an empty or managed database, or explicitly adopt a verified legacy one."""
    connection.exec_driver_sql("SET LOCAL lock_timeout='10s'")
    connection.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
    revision = current_revision(connection)
    if revision is not None:
        head = current_head(connection)
        verify_revision_schema(connection, revision=revision, head=head)
        command.upgrade(config(connection), "head")
        verify_revision_schema(connection, revision=current_revision(connection), head=head)
        return
    if not _has_database_objects(connection):
        command.upgrade(config(connection), "head")
        verify_revision_schema(
            connection, revision=current_revision(connection), head=current_head(connection)
        )
        return
    if not adopt_legacy:
        raise SchemaCompatibilityError([SchemaDifference("legacy_adoption_required")])
    verify_legacy_ledger(connection)
    adopt_baseline(connection)
    command.upgrade(config(connection), "head")
    verify_revision_schema(
        connection, revision=current_revision(connection), head=current_head(connection)
    )
