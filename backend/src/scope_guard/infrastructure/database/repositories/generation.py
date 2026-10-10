from typing import Self
from uuid import UUID

from scope_guard.infrastructure.database.repositories.drafts import Drafts
from scope_guard.infrastructure.database.repositories.projects import History, Projects
from scope_guard.modules.analysis.ports import (
    DraftGenerationRepository,
    GenerationHistoryRepository,
    GenerationProjectRepository,
)


class GenerationHistory(History):
    async def for_project(self, project: UUID):
        return await self.for_projects((project,))


class GenerationReadWork:
    """No commit capability; inherited cleanup rolls back and closes on every exit."""

    def __init__(self, work):
        self._work = work
        self.projects: GenerationProjectRepository
        self.history: GenerationHistoryRepository
        self.drafts: DraftGenerationRepository

    async def __aenter__(self) -> Self:
        await self._work.__aenter__()
        self.projects = Projects(self._work.session)
        self.history = GenerationHistory(self._work.session)
        self.drafts = Drafts(self._work.session)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self._work.__aexit__(exc_type, exc, traceback)
