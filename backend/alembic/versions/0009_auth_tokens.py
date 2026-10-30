"""One-time authentication tokens and database-backed session generations."""

from alembic import op

revision = "0009_auth_tokens"
down_revision = "0008_contextual_onboarding"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN email_verified_at timestamptz,
      ADD COLUMN session_version integer NOT NULL DEFAULT 0,
      ADD COLUMN email_verification_required boolean NOT NULL DEFAULT false,
      ADD CONSTRAINT users_session_version_check CHECK (session_version >= 0);
    ALTER TABLE users ALTER COLUMN email_verification_required SET DEFAULT true;
    CREATE TABLE auth_tokens (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES users(id),
      purpose text NOT NULL CHECK (purpose IN ('verify_email', 'reset_password')),
      token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
      created_at timestamptz NOT NULL,
      expires_at timestamptz NOT NULL,
      used_at timestamptz,
      revoked_at timestamptz,
      CONSTRAINT auth_tokens_lifetime_check CHECK (expires_at = created_at + interval '24 hours'),
      CONSTRAINT auth_tokens_state_check CHECK (used_at IS NULL OR revoked_at IS NULL)
    );
    CREATE INDEX auth_tokens_outstanding_idx ON auth_tokens(user_id, purpose)
      WHERE used_at IS NULL AND revoked_at IS NULL;
    """)


def downgrade():
    raise RuntimeError("Forward-only: retain authentication revocation evidence")
