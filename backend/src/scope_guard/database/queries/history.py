from uuid import UUID

from sqlalchemy import select

from scope_guard.database.models import DraftRow, HistoryEntryRow
from scope_guard.domain.projects.domain import (
    ProjectHistoryEntry,
)


class HistoryQueries:
    def __init__(self, session):
        self.session = session

    async def for_projects(self, identifiers: tuple[UUID, ...]) -> tuple[ProjectHistoryEntry, ...]:
        if not identifiers:
            return ()
        rows = await self.session.execute(
            select(HistoryEntryRow, DraftRow.id)
            .outerjoin(DraftRow, DraftRow.history_entry_id == HistoryEntryRow.id)
            .where(HistoryEntryRow.project_id.in_(identifiers))
            .order_by(HistoryEntryRow.date.desc())
        )
        return tuple(
            ProjectHistoryEntry(
                project_id=row.project_id,
                id=row.id,
                date=row.date,
                request=row.request,
                verdict=row.verdict,
                summary=row.summary,
                draft_id=draft,
            )
            for row, draft in rows
        )
