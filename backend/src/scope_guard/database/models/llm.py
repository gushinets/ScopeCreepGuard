"""SQLAlchemy Core mappings for the frozen ANY-663 catalog; no runtime DDL."""

import json
from pathlib import Path

from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, Numeric, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

LLM_METADATA = MetaData()


def sql_type(name):
    return {
        "uuid": UUID(as_uuid=True),
        "text": Text(),
        "integer": Integer(),
        "bigint": BigInteger(),
        "jsonb": JSONB(),
        "numeric(20,10)": Numeric(20, 10),
        "timestamp with time zone": DateTime(timezone=True),
    }[name]


manifest = json.loads(
    Path(__file__).parents[1].joinpath("0005_llm_workflow_schema.json").read_text()
)
for name, table in manifest["tables"].items():
    Table(
        name,
        LLM_METADATA,
        *(
            Column(
                c["name"],
                sql_type(c["type"]),
                nullable=not c["not_null"],
                primary_key=c["name"] == "id",
            )
            for c in table["columns"]
        ),
    )
