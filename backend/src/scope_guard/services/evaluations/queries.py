from typing import Protocol, Self
from uuid import UUID

from scope_guard.domain.evaluations.domain import EvaluationExport


class EvaluationQueries(Protocol):
    async def list_owned(self, owner: UUID) -> tuple[EvaluationExport, ...]: ...


class EvaluationReadWork(Protocol):
    evaluations: EvaluationQueries

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
