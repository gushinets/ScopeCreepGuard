"""Capture reviewed 0006 catalog from an owned disposable PostgreSQL only."""

import json
from pathlib import Path

from integration.support import DisposablePostgres
from sqlalchemy import create_engine

from alembic import command
from scope_guard.database.migrations import config, migrate
from scope_guard.database.schema_verification import inspect_profile_schema
from scope_guard.database.session import normalize_url


def main():
    with DisposablePostgres() as server, server.database() as url:
        engine = create_engine(normalize_url(url))
        try:
            with engine.begin() as connection:
                migrate(connection, target="0005_llm_workflow")
                connection.exec_driver_sql("SET LOCAL search_path TO public")
                command.upgrade(config(connection), "0006_profile_metrics")
                catalog = inspect_profile_schema(connection)
        finally:
            engine.dispose()
    target = Path(__file__).parents[2] / "src/scope_guard/database/0006_profile_metrics_schema.json"
    target.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Captured profile catalog from owned disposable PostgreSQL")


if __name__ == "__main__":
    main()
