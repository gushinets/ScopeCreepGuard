"""Persist first-use guidance on the existing profile, exempting existing users."""

from alembic import op

revision = "0008_contextual_onboarding"
down_revision = "0007_nonblocking_llm"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE profiles
      ADD COLUMN onboarding_status text NOT NULL DEFAULT 'completed',
      ADD COLUMN onboarding_step integer NOT NULL DEFAULT 4;
    ALTER TABLE profiles ALTER COLUMN onboarding_status SET DEFAULT 'not_started';
    ALTER TABLE profiles ALTER COLUMN onboarding_step SET DEFAULT 0;
    ALTER TABLE profiles ADD CONSTRAINT profiles_onboarding_check CHECK (
      (onboarding_status='not_started' AND onboarding_step=0) OR
      (onboarding_status='in_progress' AND onboarding_step BETWEEN 1 AND 3) OR
      (onboarding_status='completed' AND onboarding_step=4) OR
      (onboarding_status='skipped' AND onboarding_step BETWEEN 0 AND 3)
    );
    """)


def downgrade():
    raise RuntimeError("Forward-only: retain completed and skipped onboarding decisions")
