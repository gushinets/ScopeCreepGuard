import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

"""Catalog verification independent of Alembic's incomplete autogenerate comparison."""


TABLES = ("users", "projects", "history_entries", "drafts", "evaluation_cases")
ENUMS = ("industry", "verdict", "pricing_model", "currency", "evaluation_accuracy")


@dataclass(frozen=True)
class SchemaDifference:
    path: str


class SchemaCompatibilityError(Exception):
    def __init__(self, differences):
        self.differences = differences
        super().__init__("schema_mismatch: " + ", ".join(item.path for item in differences))


def inspect_schema(connection: Connection, table_names: tuple[str, ...] = TABLES) -> dict:
    connection.exec_driver_sql("SET LOCAL search_path TO pg_catalog, public")
    tables = {}
    for row in connection.execute(
        text("""
        SELECT c.oid, c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=ANY(:tables) ORDER BY c.relname
    """),
        {"tables": list(table_names)},
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


def verify_workflow_schema(connection: Connection, revision: str, *, extra_objects=()) -> None:
    verify_managed_schema(connection)
    for name in (
        "analysis_runs",
        "draft_revisions",
        "change_orders",
        "document_exports",
        "activity_events",
    ):
        if connection.exec_driver_sql("SELECT to_regclass('public." + name + "')").scalar() is None:
            raise SchemaCompatibilityError(
                [SchemaDifference("schema.missing_public_object." + name)]
            )
    columns: dict[str, str] = dict(
        connection.exec_driver_sql(
            "SELECT column_name,is_nullable FROM information_schema.columns W"
            "HERE table_schema='public' AND table_name='drafts'"
        )
        .tuples()
        .all()
    )
    for name in ("request_text", "revision", "analysis_is_stale", "last_analysis_run_id"):
        if name not in columns:
            raise SchemaCompatibilityError([SchemaDifference("drafts.missing." + name)])
    if (
        revision in ("0003_workflow_constraints", "0004_workflow_retire")
        and columns["revision"] != "NO"
    ):
        raise SchemaCompatibilityError([SchemaDifference("drafts.revision_nullable")])
    if revision == "0004_workflow_retire" and "history_entry_id" in columns:
        raise SchemaCompatibilityError([SchemaDifference("drafts.compatibility_not_retired")])
    table_names = TABLES + (
        "draft_revisions",
        "analysis_runs",
        "change_orders",
        "document_exports",
        "activity_events",
    )
    actual = inspect_schema(connection, table_names)
    actual["functions"] = [
        dict(row)
        for row in connection.exec_driver_sql(
            "SELECT p.proname AS name,p.prosrc AS source FROM pg_proc p JOIN pg_namespace n "
            "ON n.oid=p.pronamespace WHERE n.nspname='public' AND LEFT(p.proname,9)='workflow_' "
            "ORDER BY p.proname"
        ).mappings()
    ]
    expected_schema = json.loads(
        Path(__file__).with_name(revision + "_schema.json").read_text(encoding="utf-8")
    )
    differences = compare_schema(actual, expected_schema)
    objects = set(
        connection.exec_driver_sql(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')"
        ).scalars()
    )
    differences.extend(
        SchemaDifference("schema.unexpected_public_object." + name)
        for name in sorted(objects - set(table_names) - {"alembic_version"} - set(extra_objects))
    )
    if differences:
        raise SchemaCompatibilityError(differences)


def _verify_llm_schema_v5(connection: Connection) -> None:
    names = ("llm_operations", "llm_steps", "provider_calls")
    verify_workflow_schema(connection, "0004_workflow_retire", extra_objects=names)
    expected = json.loads(Path(__file__).with_name("0005_llm_workflow_schema.json").read_text())
    differences = compare_schema(inspect_schema(connection, names), expected)
    if differences:
        raise SchemaCompatibilityError(differences)


PROFILE_TABLES = TABLES + (
    "draft_revisions",
    "analysis_runs",
    "change_orders",
    "document_exports",
    "activity_events",
    "llm_operations",
    "llm_steps",
    "provider_calls",
    "profiles",
    "profile_preferences",
    "profile_revisions",
    "product_sessions",
    "marketing_metrics",
)


def inspect_profile_schema(connection: Connection, *, auth_tokens=False) -> dict:
    """Whole managed catalog, including all behavior and immutable guard definitions."""
    actual = inspect_schema(connection, PROFILE_TABLES + (("auth_tokens",) if auth_tokens else ()))
    actual["functions"] = [
        dict(row)
        for row in connection.exec_driver_sql(
            "SELECT p.proname AS name,p.prosrc AS source FROM pg_proc p JOIN pg_namespace n "
            "ON n.oid=p.pronamespace WHERE n.nspname='public' "
            "ORDER BY p.proname"
        ).mappings()
    ]
    return actual


def verify_profile_schema(
    connection: Connection, *, nonblocking=False, onboarding=False, auth_tokens=False
) -> None:
    verify_managed_schema(connection)
    expected = json.loads(
        Path(__file__)
        .with_name(
            "0009_auth_tokens_schema.json"
            if auth_tokens
            else "0008_contextual_onboarding_schema.json"
            if onboarding
            else "0006_profile_metrics_schema.json"
        )
        .read_text(encoding="utf-8")
    )
    if nonblocking:
        for constraint in expected["tables"]["llm_operations"]["constraints"]:
            if constraint["name"] == "llm_operations_kind_check":
                constraint["definition"] = (
                    "CHECK ((kind = ANY (ARRAY['check'::text, 'regenerate'::text, "
                    "'translate'::text, 'estimate'::text, 'agreement'::text, 'diagnostic'::text])))"
                )
    differences = compare_schema(
        inspect_profile_schema(connection, auth_tokens=auth_tokens), expected
    )
    objects = set(
        connection.exec_driver_sql(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')"
        ).scalars()
    )
    differences.extend(
        SchemaDifference("schema.unexpected_public_object." + name)
        for name in sorted(
            objects
            - set(PROFILE_TABLES)
            - ({"auth_tokens"} if auth_tokens else set())
            - {"alembic_version"}
        )
    )
    if differences:
        raise SchemaCompatibilityError(differences)


def verify_llm_schema(connection: Connection) -> None:
    """Validate supported runtime revision, retaining exact revision-specific checks."""
    revisions = (
        connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalars().all()
    )
    if revisions == ["0009_auth_tokens"]:
        verify_auth_tokens_schema(connection)
    elif revisions == ["0008_contextual_onboarding"]:
        verify_onboarding_schema(connection)
    elif revisions == ["0007_nonblocking_llm"]:
        verify_nonblocking_schema(connection)
    elif revisions == ["0006_profile_metrics"]:
        verify_profile_schema(connection)
    else:
        _verify_llm_schema_v5(connection)


def verify_nonblocking_schema(connection):
    revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    if revision == "0009_auth_tokens":
        verify_auth_tokens_schema(connection)
    elif revision == "0008_contextual_onboarding":
        verify_onboarding_schema(connection)
    else:
        verify_profile_schema(connection, nonblocking=True)


def verify_auth_tokens_schema(connection):
    verify_profile_schema(connection, auth_tokens=True)


REVISION_VALIDATORS["0009_auth_tokens"] = verify_auth_tokens_schema


def verify_onboarding_schema(connection):
    verify_profile_schema(connection, onboarding=True)


REVISION_VALIDATORS["0007_nonblocking_llm"] = verify_nonblocking_schema
REVISION_VALIDATORS["0008_contextual_onboarding"] = verify_onboarding_schema
REVISION_VALIDATORS["0005_llm_workflow"] = _verify_llm_schema_v5
REVISION_VALIDATORS["0006_profile_metrics"] = verify_profile_schema


def verify_revision_schema(connection: Connection, *, revision: str | None, head: str) -> None:
    "Validate a known Alembic state without applying legacy baseline rules to descendants."
    if revision is None:
        raise SchemaCompatibilityError([SchemaDifference("missing_alembic_revision")])
    if revision.startswith(("0002_workflow", "0003_workflow", "0004_workflow")):
        verify_workflow_schema(connection, revision)
        return
    validator = REVISION_VALIDATORS.get(revision)
    if validator is not None:
        validator(connection)
    elif revision == head:
        verify_current_head(connection)
    else:
        verify_managed_schema(connection)
