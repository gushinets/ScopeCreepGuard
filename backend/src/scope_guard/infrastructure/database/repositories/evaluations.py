from typing import Self
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.core.contracts import Verdict
from scope_guard.domain.evaluations.domain import (
    EvaluationExport,
    EvaluationLabel,
    EvaluationResult,
    OwnedHistoryContext,
)
from scope_guard.infrastructure.database.models import (
    EvaluationCaseRow,
    HistoryEntryRow,
    ProjectRow,
)
from scope_guard.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork


class Evaluations:
    def __init__(self, session: AsyncSession):
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

    async def upsert(
        self,
        owner: UUID,
        context: OwnedHistoryContext,
        label: EvaluationLabel,
        human: Verdict | None,
    ) -> EvaluationResult:
        statement = insert(EvaluationCaseRow).values(
            user_id=owner,
            history_entry_id=context.id,
            scope=context.scope,
            request=context.request,
            ai_verdict=context.ai_verdict,
            human_verdict=human,
            ai_reasoning=label.ai_reasoning,
            accuracy=label.accuracy,
            industry=context.industry,
        )
        row = await self.session.scalar(
            statement.on_conflict_do_update(
                index_elements=[EvaluationCaseRow.history_entry_id],
                set_={
                    "user_id": owner,
                    "scope": context.scope,
                    "request": context.request,
                    "ai_verdict": context.ai_verdict,
                    "human_verdict": human,
                    "ai_reasoning": label.ai_reasoning,
                    "accuracy": label.accuracy,
                    "industry": context.industry,
                    "updated_at": func.now(),
                },
            ).returning(EvaluationCaseRow)
        )
        if row is None:
            raise RuntimeError("evaluation_upsert_missing")
        return EvaluationResult(row.id, row.accuracy, row.human_verdict)

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


class EvaluationUnitOfWork:
    def __init__(self, work: SqlAlchemyUnitOfWork):
        self.work = work
        self.evaluations: Evaluations

    async def __aenter__(self) -> Self:
        await self.work.__aenter__()
        self.evaluations = Evaluations(self.work.session)
        return self

    async def commit(self) -> None:
        await self.work.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.work.__aexit__(exc_type, exc, traceback)
