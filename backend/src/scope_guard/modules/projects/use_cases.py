from collections.abc import Awaitable, Callable
from uuid import UUID

from scope_guard.domain.projects.domain import (
    ManualHistoryInput,
    Project,
    ProjectCard,
    ProjectDetail,
    ProjectHistoryEntry,
)
from scope_guard.domain.projects.errors import ProjectError
from scope_guard.domain.projects.repository import ProjectWork


def identifier(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        # Legacy project routes delegated malformed UUIDs to PostgreSQL (generic 500).
        raise ProjectError("requestFailed", 500) from None


def detail(project: Project, history: tuple[ProjectHistoryEntry, ...]) -> ProjectDetail:
    return ProjectDetail(
        project, tuple(entry for entry in history if entry.project_id == project.id)
    )


class ProjectService:
    def __init__(self, factory: Callable[[], ProjectWork]):
        self.factory = factory

    async def list(self, owner: str) -> tuple[ProjectDetail, ...]:
        async with self.factory() as work:
            projects = await work.projects.list_owned(UUID(owner))
            history = await work.history.for_projects(tuple(project.id for project in projects))
            return tuple(detail(project, history) for project in projects)

    async def get(self, owner: str, value: str) -> ProjectDetail:
        async with self.factory() as work:
            project = await work.projects.get_owned(UUID(owner), identifier(value))
            if project is None:
                raise ProjectError("projectNotFound", 404)
            history = await work.history.for_projects((project.id,))
            return detail(project, history)

    async def create(self, owner: str, card: ProjectCard) -> ProjectDetail:
        async with self.factory() as work:
            project = await work.projects.create(UUID(owner), card)
            await work.commit()
            return ProjectDetail(project)

    async def update(
        self, owner: str, value: str, read_card: Callable[[], Awaitable[ProjectCard]]
    ) -> ProjectDetail:
        async with self.factory() as work:
            key = identifier(value)
            current = await work.projects.get_owned(UUID(owner), key)
            if current is None:
                raise ProjectError("projectNotFound", 404)
            history = await work.history.for_projects((key,))
            card = await read_card()
            project = await work.projects.update(UUID(owner), key, card)
            if project is None:
                raise ProjectError("projectNotFound", 404)
            await work.commit()
            return detail(project, history)

    async def delete(self, owner: str, value: str) -> None:
        async with self.factory() as work:
            if not await work.projects.delete(UUID(owner), identifier(value)):
                raise ProjectError("projectNotFound", 404)
            await work.commit()

    async def create_history(
        self,
        owner: str,
        value: str,
        read_entry: Callable[[], Awaitable[ManualHistoryInput]],
    ) -> ProjectHistoryEntry:
        async with self.factory() as work:
            key = identifier(value)
            owner_id = UUID(owner)
            if await work.projects.get_owned(owner_id, key) is None:
                raise ProjectError("projectNotFound", 404)
            entry = await work.history.create(key, await read_entry())
            if not await work.projects.update_last_checked(owner_id, key, entry.date.isoformat()):
                raise ProjectError("projectNotFound", 404)
            await work.commit()
            return entry
