"""Only guarded tooling may provide an online connection; no URL discovery here."""

from alembic import context
from scope_guard.infrastructure.database.models import Base

connection = context.config.attributes.get("connection")
if connection is None or not context.config.attributes.get("verified_operation"):
    raise RuntimeError(
        "Use scope_guard.infrastructure.database.cli; direct Alembic mutation is disabled"
    )
context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    compare_type=True,
    compare_server_default=True,
    version_table_schema="public",
)
with context.begin_transaction():
    context.run_migrations()
