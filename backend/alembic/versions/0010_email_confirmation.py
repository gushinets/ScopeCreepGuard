"""Shared multi-process email confirmation send accounting."""

from alembic import op

revision = "0010_email_confirmation"
down_revision = "0009_auth_tokens"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE email_confirmation_attempts (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES users(id),
      source_hash text NOT NULL CHECK (source_hash ~ '^[0-9a-f]{64}$'),
      created_at timestamptz NOT NULL DEFAULT now(),
      status text NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('unknown','accepted','failed'))
    );
    CREATE INDEX email_confirmation_account_idx
      ON email_confirmation_attempts(user_id,created_at);
    CREATE INDEX email_confirmation_source_idx
      ON email_confirmation_attempts(source_hash,created_at);
    """)


def downgrade():
    raise RuntimeError("Forward-only: retain delivery accounting")
