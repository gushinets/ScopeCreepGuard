"Retire compatibility columns; original values remain in immutable legacy envelopes."

from alembic import op

revision = "0004_workflow_retire"
down_revision = "0003_workflow_constraints"
branch_labels = depends_on = None


def upgrade():
    from scope_guard.database.workflow_backfill import verify_backfill

    verify_backfill(op.get_bind())
    # Every imported row retains the complete original field set and verified digest.
    op.execute("""
    ALTER TABLE drafts DROP COLUMN history_entry_id, DROP COLUMN idempotency_key,
     DROP COLUMN project_snapshot, DROP COLUMN analysis_snapshot, DROP COLUMN locale,
     DROP COLUMN request_language, DROP COLUMN client_material_language,
     DROP COLUMN change_order_labels, DROP COLUMN status;
    DROP INDEX drafts_working_project;
    """)


def downgrade():
    raise RuntimeError("Do not recreate mutable legacy paths over immutable archives")
