"""Read-only document orchestration. Never enrich historical exports with current terms."""

from collections.abc import Callable
from uuid import UUID

from scope_guard.domain.drafts.repository import DraftWork
from scope_guard.domain.drafts.values import JsonObject, JsonValue
from scope_guard.domain.projects.repository import ProjectWork
from scope_guard.modules.drafts.use_cases import DraftError
from scope_guard.modules.projects.use_cases import ProjectError
from scope_guard.services.documents.models import DocumentError, DocumentSource


class DocumentUseCases:
    def __init__(self, drafts: Callable[[], DraftWork], projects: Callable[[], ProjectWork]):
        self.drafts, self.projects = drafts, projects

    async def saved(self, owner: UUID, draft_id: UUID) -> DocumentSource:
        async with self.drafts() as work:
            saved = await work.drafts.load_owned(owner, draft_id)
            if saved is None:
                raise DraftError("draftNotFound", 404)
            # document is the immutable saved editor state. No current-project lookup.
            editor = saved.document.get("changeOrder")
            if not isinstance(editor, JsonObject):
                raise DocumentError("pdfDocumentMissing")
            return DocumentSource(editor, saved.project_snapshot)

    async def preview(
        self, owner: UUID, project_id: UUID, draft_id: UUID | None, editor: JsonObject
    ) -> DocumentSource:
        snapshot: JsonValue = None
        if draft_id is not None:
            async with self.drafts() as work:
                saved = await work.drafts.load_owned(owner, draft_id)
                if saved is None or saved.project_id != project_id:
                    raise DraftError("draftNotFound", 404)
                snapshot = saved.project_snapshot
                # Explicit submitted edits override the saved document. Its historical
                # snapshot stays attached to the draft and is never replaced/updated.
        async with self.projects() as work:
            if await work.projects.get_owned(owner, project_id) is None:
                raise ProjectError("projectNotFound", 404)
        return DocumentSource(editor, snapshot)
