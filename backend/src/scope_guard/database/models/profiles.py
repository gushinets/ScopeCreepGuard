"""Current profile Core mappings; preferences remain unknown until explicitly set."""

from sqlalchemy import Column, Integer, Text

from scope_guard.database.models.workflow import WORKFLOW_METADATA

profiles = WORKFLOW_METADATA.tables["profiles"]
profile_preferences = WORKFLOW_METADATA.tables["profile_preferences"]
profile_revisions = WORKFLOW_METADATA.tables["profile_revisions"]
product_sessions = WORKFLOW_METADATA.tables["product_sessions"]

# First-use state is independent of business profile revisions.
profiles.append_column(Column("onboarding_status", Text(), nullable=False))
profiles.append_column(Column("onboarding_step", Integer(), nullable=False))
