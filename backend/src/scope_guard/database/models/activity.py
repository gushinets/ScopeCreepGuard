"""Current behavior events: NULL contract is historical; version 2 is explicit."""

from scope_guard.database.models.workflow import WORKFLOW_METADATA

activity_events = WORKFLOW_METADATA.tables["activity_events"]
