"""One-time deliberate reference generation. Never called by application or tests."""

import json

from sqlalchemy import create_engine
from support import ROOT, DisposablePostgres, migration_digest, replay_drizzle

from scope_guard.database.schema_verification import inspect_schema

if __name__ == "__main__":
    fixture = ROOT / "backend/tests/fixtures/legacy_drizzle"
    journal = json.loads((fixture / "_journal.json").read_text())
    with DisposablePostgres() as server, server.database() as url:
        replay_drizzle(url)
        engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://"))
        try:
            with engine.begin() as connection:
                schema = inspect_schema(connection)
        finally:
            engine.dispose()
    provenance = [
        {
            "tag": item["tag"],
            "when": item["when"],
            "sha256": migration_digest((fixture / (item["tag"] + ".sql")).read_bytes()),
        }
        for item in journal["entries"]
    ]
    target = ROOT / "backend/src/scope_guard/database/baseline_schema.json"
    target.write_text(
        json.dumps(
            {
                "postgres_major": 17,
                "drizzle_hash_normalization": "CRLF to LF",
                "drizzle": provenance,
                "schema": schema,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
