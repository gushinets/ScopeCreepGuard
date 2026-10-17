"""Baseline-only ORM aliases for explicitly retained pre-workflow read/write adapters.

These map the historical Drizzle baseline, not the supported current Alembic head.
Current workflow code uses models.workflow (Core) or specialized verified SQL.
"""

from .drafts import CompatibilityDraftRow as CompatibilityDraftRow
from .evaluations import EvaluationCaseRow as CompatibilityEvaluationCaseRow
from .history import HistoryEntryRow as CompatibilityHistoryEntryRow
from .projects import ProjectRow as CompatibilityProjectRow

__all__ = [
    "CompatibilityDraftRow",
    "CompatibilityEvaluationCaseRow",
    "CompatibilityHistoryEntryRow",
    "CompatibilityProjectRow",
]
