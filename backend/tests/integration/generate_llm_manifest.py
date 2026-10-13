"""Capture only the new revision's catalog on owned disposable PostgreSQL."""

import json
from pathlib import Path

from integration.support import DisposablePostgres
from sqlalchemy import create_engine

from alembic import command
from scope_guard.database.migrations import config, migrate
from scope_guard.database.schema_verification import inspect_schema
from scope_guard.database.session import normalize_url


def main():
    with DisposablePostgres() as server, server.database() as url:
        engine = create_engine(normalize_url(url))
        with engine.begin() as connection:
            migrate(connection, target="0004_workflow_retire")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            # Bootstrap the new manifest only. Normal migrations verify it on every run.
            command.upgrade(config(connection), "0005_llm_workflow")
            catalog = inspect_schema(connection, ("llm_operations", "llm_steps", "provider_calls"))
        engine.dispose()
    target = Path(__file__).parents[2] / "src/scope_guard/database/0005_llm_workflow_schema.json"
    target.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Captured ANY-663 catalog from owned disposable PostgreSQL only")


if __name__ == "__main__":
    main()
