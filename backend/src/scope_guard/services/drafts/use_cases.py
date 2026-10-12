from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from scope_guard.domain.drafts.repository import DraftWork
from scope_guard.domain.drafts.values import (
    CreatedDraft,
    CreateDraft,
    DraftDocument,
    DraftSummary,
    StoredDraft,
)
from scope_guard.services.drafts.queries import DraftReadWork


class DraftError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = "errors." + code, status
        super().__init__(self.code)


class DraftService:
    def __init__(
        self,
        factory: Callable[[], DraftWork],
        clock: Callable[[], float],
        reads: Callable[[], DraftReadWork] | None = None,
    ):
        self.factory, self.clock = factory, clock
        self.reads = reads or factory

    async def list(self, owner: UUID) -> tuple[DraftSummary, ...]:
        async with self.reads() as work:
            return await work.drafts.list_owned(owner)

    async def get(self, owner: UUID, identifier: UUID) -> StoredDraft:
        async with self.factory() as work:
            draft = await work.drafts.load_owned(owner, identifier)
            if draft is None:
                raise DraftError("draftNotFound", 404)
            return draft

    async def create(self, owner: UUID, command: CreateDraft) -> CreatedDraft:
        async with self.factory() as work:
            if not await work.drafts.lock_project(owner, command.project_id):
                raise DraftError("projectNotFound", 404)
            existing = await work.drafts.find_creation(
                owner, command.project_id, command.idempotency_key
            )
            if existing is not None:
                return existing
            now = datetime.fromtimestamp(self.clock(), UTC)
            history = await work.drafts.insert_history(owner, command, now.date())
            draft = await work.drafts.insert_draft(owner, command, history, now)
            await work.drafts.mark_checked(owner, command.project_id, now.date())
            entry = await work.drafts.history_for_draft(owner, draft)
            outcome = CreatedDraft(draft, entry, True)
            await work.commit()
            return outcome

    async def update(
        self,
        owner: UUID,
        identifier: UUID,
        read_document: Callable[[StoredDraft], Awaitable[DraftDocument]],
    ) -> StoredDraft:
        async with self.factory() as work:
            saved = await work.drafts.load_owned(owner, identifier)
            if saved is None:
                raise DraftError("draftNotFound", 404)
            document = await read_document(saved)
            updated = await work.drafts.update_document(
                owner, identifier, document, datetime.fromtimestamp(self.clock(), UTC)
            )
            if updated is None:
                raise DraftError("draftNotFound", 404)
            await work.commit()
            return updated
