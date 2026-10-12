"""Read DTOs and ports, independent of aggregate mutation implementations."""

from typing import Protocol, Self
from uuid import UUID

from scope_guard.domain.projects.domain import Project, ProjectHistoryEntry


class ProjectQueries(Protocol):
    async def list_owned(self, owner: UUID) -> tuple[Project, ...]: ...


class HistoryQueries(Protocol):
    async def for_projects(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[ProjectHistoryEntry, ...]: ...


class ProjectReadWork(Protocol):
    projects: ProjectQueries
    history: HistoryQueries

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
