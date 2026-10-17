from uuid import UUID

from sqlalchemy import func, select

from scope_guard.database.models import HistoryEntryRow, ProjectRow
from scope_guard.database.models.compatibility import CompatibilityDraftRow as DraftRow
from scope_guard.domain.drafts.values import (
    DraftSummary,
)

"""Owned persistence with no transaction lifecycle outside the inherited UoW."""


class DraftQueries:
    def __init__(self, session):
        self.session = session

    async def list_owned(self, owner: UUID) -> tuple[DraftSummary, ...]:
        name = func.coalesce(
            DraftRow.project_snapshot["name"].astext,
            DraftRow.draft_document["changeOrder"]["projectName"].astext,
            ProjectRow.name,
        )
        rows = await self.session.execute(
            select(
                DraftRow.id,
                HistoryEntryRow.request,
                name,
                HistoryEntryRow.verdict,
                DraftRow.created_at,
                DraftRow.updated_at,
            )
            .join(ProjectRow, ProjectRow.id == DraftRow.project_id)
            .join(HistoryEntryRow, HistoryEntryRow.id == DraftRow.history_entry_id)
            .where(ProjectRow.user_id == owner)
            .order_by(DraftRow.created_at.desc(), DraftRow.id.desc())
        )
        return tuple(DraftSummary(*row) for row in rows)


class DraftReadWork:
    def __init__(self, work):
        self.work = work

    async def __aenter__(self):
        await self.work.__aenter__()
        self.drafts = DraftQueries(self.work.session)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.work.__aexit__(exc_type, exc, traceback)
