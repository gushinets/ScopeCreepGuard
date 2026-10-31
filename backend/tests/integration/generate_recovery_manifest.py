"""One-off catalog capture on owned disposable PostgreSQL; never application startup."""

import importlib.util
import json
from pathlib import Path

from integration.support import DisposablePostgres, prepare_alembic
from sqlalchemy import create_engine

from scope_guard.database.schema_verification import inspect_profile_schema, inspect_schema


def main():
    spec = importlib.util.spec_from_file_location(
        "recovery_migration", "alembic/versions/0011_password_recovery.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with DisposablePostgres() as server, server.database() as url:
        prepare_alembic(url, target="0010_email_confirmation")
        engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://"))
        with engine.begin() as db:
            db.exec_driver_sql(migration.SQL)
            catalog = inspect_profile_schema(db, auth_tokens=True, email_confirmation=True)
            catalog["tables"].update(
                inspect_schema(db, ("email_jobs", "recovery_limits"))["tables"]
            )
            Path("src/scope_guard/database/0011_password_recovery_schema.json").write_text(
                json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        engine.dispose()


if __name__ == "__main__":
    main()
