from typing import Self
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.database.legacy_boundary import require_legacy_schema
from scope_guard.database.models import (
    EvaluationCaseRow,
)
from scope_guard.database.queries.evaluations import EvaluationQueries
from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.domain.evaluations.domain import (
    EvaluationLabel,
    EvaluationResult,
    OwnedHistoryContext,
)
from scope_guard.domain.shared.enums import Verdict


class Evaluations(EvaluationQueries):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        owner: UUID,
        context: OwnedHistoryContext,
        label: EvaluationLabel,
        human: Verdict | None,
    ) -> EvaluationResult:
        await require_legacy_schema(self.session)
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
