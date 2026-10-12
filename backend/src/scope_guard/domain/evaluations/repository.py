from typing import Protocol, Self
from uuid import UUID

from scope_guard.domain.evaluations.domain import (
    EvaluationExport,
    EvaluationLabel,
    EvaluationResult,
    OwnedHistoryContext,
)
from scope_guard.domain.shared.enums import Verdict


class EvaluationRepository(Protocol):
    async def history_owned(self, owner: UUID, history: UUID) -> OwnedHistoryContext | None: ...
    async def upsert(
        self,
        owner: UUID,
        context: OwnedHistoryContext,
        label: EvaluationLabel,
        human: Verdict | None,
    ) -> EvaluationResult: ...
    async def list_owned(self, owner: UUID) -> tuple[EvaluationExport, ...]: ...


class EvaluationWork(Protocol):
    @property
    def evaluations(self) -> EvaluationRepository: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
    async def commit(self) -> None: ...
