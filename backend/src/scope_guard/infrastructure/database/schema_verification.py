"""Catalog verification independent of Alembic's incomplete autogenerate comparison."""

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

TABLES = ("users", "projects", "history_entries", "drafts", "evaluation_cases")
ENUMS = ("industry", "verdict", "pricing_model", "currency", "evaluation_accuracy")


@dataclass(frozen=True)
class SchemaDifference:
    path: str


class SchemaCompatibilityError(Exception):
    def __init__(self, differences):
        self.differences = differences
        super().__init__("schema_mismatch: " + ", ".join(item.path for item in differences))


def inspect_schema(connection: Connection) -> dict:
    connection.exec_driver_sql("SET LOCAL search_path TO pg_catalog, public")
    tables = {}
    for row in connection.execute(
        text("""
        SELECT c.oid, c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=ANY(:tables) ORDER BY c.relname
    """),
        {"tables": list(TABLES)},
    ).mappings():
        oid = row["oid"]
        tables[row["relname"]] = {
            "kind": row["relkind"],
            "rls": row["relrowsecurity"],
            "force_rls": row["relforcerowsecurity"],
            "columns": [
                dict(item)
                for item in connection.execute(
                    text("""
                SELECT a.attname AS name, format_type(a.atttypid,a.atttypmod) AS type,
                    a.attnotnull AS not_null, pg_get_expr(d.adbin,d.adrelid,false) AS default,
                    a.attidentity AS identity, a.attgenerated AS generated
                FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND
d.adnum=a.attnum
                WHERE a.attrelid=:oid AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attname
            """),
                    {"oid": oid},
                ).mappings()
            ],
            "constraints": [
                dict(item)
                for item in connection.execute(
                    text("""
                SELECT conname AS name, contype AS type,
                    pg_get_constraintdef(oid,false) AS definition, convalidated AS validated,
                    condeferrable AS deferrable, condeferred AS deferred
                FROM pg_constraint WHERE conrelid=:oid ORDER BY conname
            """),
                    {"oid": oid},
                ).mappings()
            ],
            "indexes": [
                dict(item)
                for item in connection.execute(
                    text("""
                SELECT c.relname AS name, pg_get_indexdef(i.indexrelid,0,false) AS definition,
                    i.indisvalid AS valid, i.indisready AS ready, i.indnullsnotdistinct AS
nulls_not_distinct
                FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
                WHERE i.indrelid=:oid ORDER BY c.relname
            """),
                    {"oid": oid},
                ).mappings()
            ],
            "triggers": [
                dict(item)
                for item in connection.execute(
                    text("""
                SELECT tgname AS name, pg_get_triggerdef(oid,false) AS definition, tgenabled AS
enabled
                FROM pg_trigger WHERE tgrelid=:oid AND NOT tgisinternal ORDER BY tgname
            """),
                    {"oid": oid},
                ).mappings()
            ],
        }
    enums: dict[str, list[str]] = {}
    for enum_row in connection.execute(
        text("""
        SELECT t.typname, e.enumlabel FROM pg_type t
        JOIN pg_namespace n ON n.oid=t.typnamespace JOIN pg_enum e ON e.enumtypid=t.oid
        WHERE n.nspname='public' AND t.typname=ANY(:enums) ORDER BY t.typname,e.enumsortorder
    """),
        {"enums": list(ENUMS)},
    ):
        enums.setdefault(enum_row.typname, []).append(enum_row.enumlabel)
    return {"tables": tables, "enums": enums}


def compare_schema(actual: dict, expected: dict) -> list[SchemaDifference]:
    differences = []

    def compare(left, right, path):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left or key not in right:
                    differences.append(SchemaDifference(path + "." + key))
                else:
                    compare(left[key], right[key], path + "." + key)
        elif left != right:
            differences.append(SchemaDifference(path))

    compare(actual, expected, "schema")
    return differences


def verify_baseline(connection: Connection) -> None:
    major = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one()) // 10000
    if major != 17:
        raise SchemaCompatibilityError([SchemaDifference("server_major_requires_17")])
    expected = json.loads(
        Path(__file__).with_name("baseline_schema.json").read_text(encoding="utf-8")
    )
    differences = compare_schema(inspect_schema(connection), expected["schema"])
    public_objects = set(
        connection.exec_driver_sql("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')
        """).scalars()
    )
    allowed_objects = set(TABLES) | {"alembic_version"}
    for name in sorted(public_objects - allowed_objects):
        differences.append(SchemaDifference("schema.unexpected_public_object." + name))
    public_enums = set(
        connection.exec_driver_sql("""
            SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
            WHERE n.nspname='public' AND t.typtype='e'
        """).scalars()
    )
    for name in sorted(public_enums - set(ENUMS)):
        differences.append(SchemaDifference("schema.unexpected_public_enum." + name))
    if differences:
        raise SchemaCompatibilityError(differences)


def verify_managed_schema(connection: Connection) -> None:
    """Check the invariant application boundary shared by all Alembic revisions."""
    major = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one()) // 10000
    if major != 17:
        raise SchemaCompatibilityError([SchemaDifference("server_major_requires_17")])
    public_objects = set(
        connection.exec_driver_sql("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')
        """).scalars()
    )
    differences = [
        SchemaDifference("schema.missing_public_object." + name)
        for name in sorted((set(TABLES) | {"alembic_version"}) - public_objects)
    ]
    public_enums = set(
        connection.exec_driver_sql("""
            SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
            WHERE n.nspname='public' AND t.typtype='e'
        """).scalars()
    )
    differences.extend(
        SchemaDifference("schema.missing_public_enum." + name)
        for name in sorted(set(ENUMS) - public_enums)
    )
    if differences:
        raise SchemaCompatibilityError(differences)


def verify_current_head(connection: Connection) -> None:
    """Validate the active Alembic head's shared application boundary."""
    verify_managed_schema(connection)


REVISION_VALIDATORS = {"0001_existing_drizzle_schema": verify_baseline}


def verify_revision_schema(connection: Connection, *, revision: str | None, head: str) -> None:
    """Validate a known Alembic state without applying legacy baseline rules to descendants."""
    if revision is None:
        raise SchemaCompatibilityError([SchemaDifference("missing_alembic_revision")])
    validator = REVISION_VALIDATORS.get(revision)
    if validator is not None:
        validator(connection)
    elif revision == head:
        verify_current_head(connection)
    else:
        verify_managed_schema(connection)
