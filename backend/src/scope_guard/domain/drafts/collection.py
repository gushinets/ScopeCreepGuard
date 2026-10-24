"""Read-only current Draft filters, independent of HTTP and persistence."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class DraftCollectionFilter:
    project_id: UUID | None = None
    created_from: date | None = None
    created_to: date | None = None
    sort: Literal["newest", "oldest"] = "newest"

    def parameters(self) -> dict:
        return {
            "project": self.project_id,
            "created_from": datetime.combine(self.created_from, time.min, UTC)
            if self.created_from
            else None,
            "created_before": datetime.combine(self.created_to + timedelta(days=1), time.min, UTC)
            if self.created_to
            else None,
        }
