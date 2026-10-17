from uuid import UUID

from sqlalchemy import select, text

from scope_guard.database.models import HistoryEntryRow
from scope_guard.database.models.compatibility import CompatibilityDraftRow as DraftRow
from scope_guard.domain.projects.domain import (
    ProjectHistoryEntry,
)


class HistoryQueries:
    def __init__(self, session):
        self.session = session

    async def for_projects(self, identifiers: tuple[UUID, ...]) -> tuple[ProjectHistoryEntry, ...]:
        if not identifiers:
            return ()
        # Baseline adapters remain available during the guarded rollout. Current
        # history owns its source-draft link; retired draft columns are never read.
        supported = await self.session.scalar(
            text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='history_entries' "
                "AND column_name='source_draft_id')"
            )
        )
        if supported:
            from scope_guard.database.models.workflow import history_entries

            rows = (
                await self.session.execute(
                    select(history_entries)
                    .where(history_entries.c.project_id.in_(identifiers))
                    .order_by(history_entries.c.date.desc(), history_entries.c.id)
                )
            ).mappings()
            return tuple(
                ProjectHistoryEntry(
                    project_id=row["project_id"],
                    id=row["id"],
                    date=row["date"],
                    request=row["request"],
                    verdict=row["verdict"],
                    summary=row["summary"],
                    draft_id=row["source_draft_id"],
                )
                for row in rows
            )
        rows = await self.session.execute(
            select(HistoryEntryRow, DraftRow.id)
            .outerjoin(DraftRow, DraftRow.history_entry_id == HistoryEntryRow.id)
            .where(HistoryEntryRow.project_id.in_(identifiers))
            .order_by(HistoryEntryRow.date.desc())
        )
        return tuple(
            ProjectHistoryEntry(
                project_id=row.project_id,
                id=row.id,
                date=row.date,
                request=row.request,
                verdict=row.verdict,
                summary=row.summary,
                draft_id=draft,
            )
            for row, draft in rows
        )
