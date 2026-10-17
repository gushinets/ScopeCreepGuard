"""Wide daily marketing row with explicit nullable typed KPI columns, no EAV values."""

from scope_guard.database.models.workflow import WORKFLOW_METADATA

marketing_metrics = WORKFLOW_METADATA.tables["marketing_metrics"]
