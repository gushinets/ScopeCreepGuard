from typing import Protocol, Self
from uuid import UUID

from scope_guard.domain.drafts.values import DraftSummary


class DraftQueries(Protocol):
    async def list_owned(self, owner: UUID) -> tuple[DraftSummary, ...]: ...


class DraftReadWork(Protocol):
    drafts: DraftQueries

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
