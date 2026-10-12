from uuid import UUID

from sqlalchemy import select

from scope_guard.database.models import (
    EvaluationCaseRow,
    HistoryEntryRow,
    ProjectRow,
)
from scope_guard.domain.evaluations.domain import (
    EvaluationExport,
    OwnedHistoryContext,
)


class EvaluationQueries:
    def __init__(self, session):
        self.session = session

    async def history_owned(self, owner: UUID, history: UUID) -> OwnedHistoryContext | None:
        row = (
            await self.session.execute(
                select(HistoryEntryRow, ProjectRow)
                .join(ProjectRow, HistoryEntryRow.project_id == ProjectRow.id)
                .where(HistoryEntryRow.id == history, ProjectRow.user_id == owner)
            )
        ).first()
        if row is None:
            return None
        entry, project = row
        return OwnedHistoryContext(
            entry.id, project.scope, entry.request, entry.verdict, project.industry
        )

    async def list_owned(self, owner: UUID) -> tuple[EvaluationExport, ...]:
        rows = await self.session.scalars(
            select(EvaluationCaseRow)
            .where(EvaluationCaseRow.user_id == owner)
            .order_by(EvaluationCaseRow.created_at.asc(), EvaluationCaseRow.id.asc())
        )
        return tuple(
            EvaluationExport(
                row.scope,
                row.request,
                row.ai_verdict,
                row.human_verdict,
                row.ai_reasoning,
                row.industry,
            )
            for row in rows
        )


class EvaluationReadWork:
    def __init__(self, work):
        self.work = work

    async def __aenter__(self):
        await self.work.__aenter__()
        self.evaluations = EvaluationQueries(self.work.session)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.work.__aexit__(exc_type, exc, traceback)
