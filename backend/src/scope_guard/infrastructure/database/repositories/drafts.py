from typing import cast
from uuid import UUID

from sqlalchemy import select

from scope_guard.infrastructure.database.models import DraftRow, HistoryEntryRow, ProjectRow
from scope_guard.modules.analysis.domain import freeze
from scope_guard.modules.drafts.generation_context import HistoricalGenerationDraft


class Drafts:
    def __init__(self, session):
        self._session = session

    async def get_owned(self, owner: UUID, identifier: UUID) -> HistoricalGenerationDraft | None:
        result = (
            await self._session.execute(
                select(DraftRow, HistoryEntryRow.request)
                .join(ProjectRow, DraftRow.project_id == ProjectRow.id)
                .join(HistoryEntryRow, DraftRow.history_entry_id == HistoryEntryRow.id)
                .where(DraftRow.id == identifier, ProjectRow.user_id == owner)
            )
        ).first()
        if result is None:
            return None
        row, request = result
        document = row.draft_document
        co = document.get("changeOrder") or {}
        details = document.get("projectDetails") or {}
        return HistoricalGenerationDraft(
            str(row.project_id),
            request,
            freeze(row.project_snapshot) if row.project_snapshot is not None else None,
            co.get("projectName") or "",
            cast(str, details.get("clientName"))
            if details.get("clientName") is not None
            else co.get("clientName") or "",
        )
