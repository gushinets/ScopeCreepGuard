"""Supported Core column mappings for the exact 0009 catalog; never runtime DDL.

The frozen, migration-tested catalog is the column source of truth. Database
constraints/triggers remain Alembic-owned and verified independently at startup.
Legacy ORM mappings are deliberately separate because baseline read paths remain
available during migration. Do not use those mappings to describe the current schema.
"""

import json
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from scope_guard.database.models.base import accuracy, currency, industry, pricing_model, verdict

WORKFLOW_METADATA = MetaData()


def sql_type(name):
    if name.startswith("numeric("):
        precision, scale = map(int, name[8:-1].split(","))
        return Numeric(precision, scale)
    return {
        "uuid": UUID(as_uuid=True),
        "text": Text(),
        "integer": Integer(),
        "bigint": BigInteger(),
        "jsonb": JSONB(),
        "boolean": Boolean(),
        "date": Date(),
        "timestamp with time zone": DateTime(timezone=True),
        "industry": industry,
        "verdict": verdict,
        "pricing_model": pricing_model,
        "currency": currency,
        "evaluation_accuracy": accuracy,
    }[name]


_manifest = json.loads(
    Path(__file__)
    .parents[1]
    .joinpath("0010_email_confirmation_schema.json")
    .read_text(encoding="utf-8")
)
for _name, _table in _manifest["tables"].items():
    _primary_key = {"profile_preferences": "profile_id", "marketing_metrics": "report_date"}.get(
        _name, "id"
    )
    Table(
        _name,
        WORKFLOW_METADATA,
        *(
            Column(
                c["name"],
                sql_type(c["type"]),
                nullable=not c["not_null"],
                primary_key=c["name"] == _primary_key,
                server_default=text(c["default"]) if c["default"] is not None else None,
            )
            for c in _table["columns"]
        ),
    )

projects = WORKFLOW_METADATA.tables["projects"]
drafts = WORKFLOW_METADATA.tables["drafts"]
draft_revisions = WORKFLOW_METADATA.tables["draft_revisions"]
analysis_runs = WORKFLOW_METADATA.tables["analysis_runs"]
history_entries = WORKFLOW_METADATA.tables["history_entries"]
change_orders = WORKFLOW_METADATA.tables["change_orders"]
document_exports = WORKFLOW_METADATA.tables["document_exports"]
evaluation_cases = WORKFLOW_METADATA.tables["evaluation_cases"]
