from collections.abc import Callable
from typing import Protocol, Self
from uuid import UUID

from scope_guard.modules.analysis.domain import (
    AnalysisInput,
    AnalysisResult,
    ClientMaterials,
    DraftProofBinding,
    DraftProofClaims,
    MaterialInput,
    ReplyInput,
)
from scope_guard.modules.drafts.generation_context import HistoricalGenerationDraft
from scope_guard.modules.projects.domain import Project, ProjectHistoryEntry


class GenerationProjectRepository(Protocol):
    async def get_owned(self, owner: UUID, project: UUID) -> Project | None: ...


class GenerationHistoryRepository(Protocol):
    async def for_project(self, project: UUID) -> tuple[ProjectHistoryEntry, ...]: ...


class DraftGenerationRepository(Protocol):
    async def get_owned(self, owner: UUID, draft: UUID) -> HistoricalGenerationDraft | None: ...


class GenerationReadWork(Protocol):
    projects: GenerationProjectRepository
    history: GenerationHistoryRepository
    drafts: DraftGenerationRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...


class GenerationPort(Protocol):
    async def analyze(self, value: AnalysisInput) -> AnalysisResult: ...
    async def regenerate_reply(self, value: ReplyInput) -> str: ...
    async def translate_materials(self, value: MaterialInput) -> ClientMaterials: ...


class DraftProofPort(Protocol):
    def issue(self, claims: DraftProofClaims) -> str: ...
    def verify(self, token: object, expected_binding: DraftProofBinding) -> DraftProofClaims: ...


class LimiterPort(Protocol):
    def allow(self, user_id: str, now_ms: int) -> bool: ...


ReadWorkFactory = Callable[[], GenerationReadWork]
