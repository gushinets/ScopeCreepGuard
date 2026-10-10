"""Test-only descendant revision used to prove guarded lineage upgrades."""

from alembic import op

revision = "0002_revision_probe"
down_revision = "0001_existing_drizzle_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TABLE public.revision_probe (id integer PRIMARY KEY)")


def downgrade():
    op.execute("DROP TABLE public.revision_probe")
