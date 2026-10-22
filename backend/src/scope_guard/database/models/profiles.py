"""Current profile Core mappings; preferences remain unknown until explicitly set."""

from scope_guard.database.models.workflow import WORKFLOW_METADATA

profiles = WORKFLOW_METADATA.tables["profiles"]
profile_preferences = WORKFLOW_METADATA.tables["profile_preferences"]
profile_revisions = WORKFLOW_METADATA.tables["profile_revisions"]
product_sessions = WORKFLOW_METADATA.tables["product_sessions"]
