"""Only guarded tooling may provide an online connection; no URL discovery here."""

import logging

from alembic import context
from scope_guard.database.models import Base

connection = context.config.attributes.get("connection")
if connection is None or not context.config.attributes.get("verified_operation"):
    raise RuntimeError("Use scope_guard.database.cli; direct Alembic mutation is disabled")


def revision_applied(ctx, step, heads, run_args):
    logging.getLogger("scope_guard.migration").info(
        "migration_revision_applied revisions=%s", ",".join(step.up_revision_ids)
    )


context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    compare_type=True,
    compare_server_default=True,
    version_table_schema="public",
    on_version_apply=revision_applied,
)
with context.begin_transaction():
    context.run_migrations()
