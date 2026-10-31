"""Durable password recovery delivery and bounded request accounting."""

from alembic import op

revision = "0011_password_recovery"
down_revision = "0010_email_confirmation"
branch_labels = depends_on = None

SQL = """
ALTER TABLE users ADD COLUMN password_changed_at timestamptz;
CREATE INDEX auth_tokens_reset_cleanup_idx ON auth_tokens(expires_at)
 WHERE purpose='reset_password';
CREATE TABLE email_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 purpose text NOT NULL CHECK (purpose IN ('password_recovery','password_changed')),
 recipient text NOT NULL CHECK (length(recipient) <= 320),
 user_id uuid REFERENCES users(id),
 locale text NOT NULL CHECK (locale IN ('ru','en')),
 state text NOT NULL DEFAULT 'pending'
   CHECK (state IN ('pending','leased','accepted','cancelled','failed')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 expires_at timestamptz NOT NULL DEFAULT (clock_timestamp()+interval '24 hours'),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
 next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 lease_owner uuid,
 lease_expires_at timestamptz,
 token_hash text CHECK (token_hash IS NULL OR token_hash ~ '^[0-9a-f]{64}$'),
 failure_category text CHECK (failure_category IN
   ('invalid','temporary','authentication','rejected','ambiguous','expired'))
);
CREATE INDEX email_jobs_claim_idx ON email_jobs(next_attempt_at,created_at)
 WHERE state IN ('pending','leased');
CREATE INDEX email_jobs_cleanup_idx ON email_jobs(updated_at)
 WHERE state IN ('accepted','cancelled','failed');
CREATE TABLE recovery_limits (
 id text PRIMARY KEY,
 window_started_at timestamptz NOT NULL,
 count integer NOT NULL CHECK (count >= 0),
 expires_at timestamptz NOT NULL
);
CREATE INDEX recovery_limits_cleanup_idx ON recovery_limits(expires_at);
"""


def upgrade():
    op.execute(SQL)


def downgrade():
    raise RuntimeError("Forward-only: retain recovery delivery and abuse accounting")
