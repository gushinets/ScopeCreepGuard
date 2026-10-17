"""Separate explicit agreement and post-publication diagnostic operations."""

from alembic import op

revision = "0007_nonblocking_llm"
down_revision = "0006_profile_metrics"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE llm_operations DROP CONSTRAINT llm_operations_kind_check;
    ALTER TABLE llm_operations ADD CONSTRAINT llm_operations_kind_check
      CHECK(kind IN ('check','regenerate','translate','estimate','agreement','diagnostic'));
    """)


def downgrade():
    raise RuntimeError("Forward-only: retain completed agreement/diagnostic accounting")
