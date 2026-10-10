"""Owned persistence with no transaction lifecycle outside the inherited UoW."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.infrastructure.database.models import DraftRow, HistoryEntryRow, ProjectRow
from scope_guard.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.modules.analysis.domain import ABSENT, Labels
from scope_guard.modules.drafts.serialization import document_to_wire
from scope_guard.modules.drafts.values import (
    CreatedDraft,
    CreateDraft,
    DraftDocument,
    DraftHistory,
    DraftSummary,
    StoredDraft,
    freeze_json,
    freeze_object,
    language_metadata,
    thaw_json,
)


def stored(row: DraftRow, request: str) -> StoredDraft:
    return StoredDraft(
        row.id,
        row.project_id,
        row.history_entry_id,
        request,
        row.created_at,
        row.updated_at,
        row.locale,
        row.request_language,
        row.client_material_language,
        freeze_json(row.project_snapshot),
        freeze_object(row.analysis_snapshot),
        freeze_object(row.draft_document),
    )


class DraftRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def owned(self, owner: UUID):
        return (
            select(DraftRow, HistoryEntryRow)
            .join(ProjectRow, ProjectRow.id == DraftRow.project_id)
            .join(HistoryEntryRow, HistoryEntryRow.id == DraftRow.history_entry_id)
            .where(ProjectRow.user_id == owner)
        )

    async def load_owned(self, owner: UUID, identifier: UUID) -> StoredDraft | None:
        result = (
            await self.session.execute(self.owned(owner).where(DraftRow.id == identifier))
        ).first()
        return stored(result[0], result[1].request) if result else None

    async def list_owned(self, owner: UUID) -> tuple[DraftSummary, ...]:
        name = func.coalesce(
            DraftRow.project_snapshot["name"].astext,
            DraftRow.draft_document["changeOrder"]["projectName"].astext,
            ProjectRow.name,
        )
        rows = await self.session.execute(
            select(
                DraftRow.id,
                HistoryEntryRow.request,
                name,
                HistoryEntryRow.verdict,
                DraftRow.created_at,
                DraftRow.updated_at,
            )
            .join(ProjectRow, ProjectRow.id == DraftRow.project_id)
            .join(HistoryEntryRow, HistoryEntryRow.id == DraftRow.history_entry_id)
            .where(ProjectRow.user_id == owner)
            .order_by(DraftRow.created_at.desc(), DraftRow.id.desc())
        )
        return tuple(DraftSummary(*row) for row in rows)

    async def lock_project(self, owner: UUID, identifier: UUID) -> bool:
        return (
            await self.session.scalar(
                select(ProjectRow.id)
                .where(ProjectRow.id == identifier, ProjectRow.user_id == owner)
                .with_for_update()
            )
        ) is not None

    async def find_creation(self, owner: UUID, project: UUID, key: UUID) -> CreatedDraft | None:
        result = (
            await self.session.execute(
                self.owned(owner).where(
                    DraftRow.project_id == project, DraftRow.idempotency_key == key
                )
            )
        ).first()
        if result is None:
            return None
        row, history = result
        return CreatedDraft(
            stored(row, history.request), self.history_value(history, row.id), False
        )

    async def insert_history(self, owner: UUID, command: CreateDraft, day: date) -> UUID:
        # The use case holds the owned project lock throughout all three writes.
        snapshot = thaw_json(command.analysis_snapshot)
        row = HistoryEntryRow(
            project_id=command.project_id,
            date=day,
            request=command.request,
            verdict=snapshot["verdict"],
            summary=snapshot["summary"],
        )
        self.session.add(row)
        await self.session.flush()
        return row.id

    async def insert_draft(
        self, owner: UUID, command: CreateDraft, history: UUID, now: datetime
    ) -> StoredDraft:
        metadata = language_metadata(command.document)
        request_language = command.analysis_snapshot.get("requestLanguage")
        row = DraftRow(
            project_id=command.project_id,
            history_entry_id=history,
            idempotency_key=command.idempotency_key,
            project_snapshot=thaw_json(command.project_snapshot),
            analysis_snapshot=thaw_json(command.analysis_snapshot),
            draft_document=document_to_wire(command.document),
            locale=command.locale,
            request_language=request_language if request_language != ABSENT else None,
            client_material_language=metadata.language,
            change_order_labels=dict(metadata.labels.values)
            if isinstance(metadata.labels, Labels)
            else None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return stored(row, command.request)

    async def mark_checked(self, owner: UUID, project: UUID, day: date) -> None:
        await self.session.execute(
            update(ProjectRow)
            .where(ProjectRow.id == project, ProjectRow.user_id == owner)
            .values(last_checked=day)
        )

    @staticmethod
    def history_value(row: HistoryEntryRow, draft: UUID) -> DraftHistory:
        return DraftHistory(
            row.id, row.project_id, row.date, row.request, row.verdict, row.summary, draft
        )

    async def history_for_draft(self, owner: UUID, draft: StoredDraft) -> DraftHistory:
        result = (
            await self.session.execute(self.owned(owner).where(DraftRow.id == draft.id))
        ).one()
        return self.history_value(result[1], draft.id)

    async def update_document(
        self, owner: UUID, identifier: UUID, document: DraftDocument, now: datetime
    ) -> StoredDraft | None:
        metadata = language_metadata(document)
        owned_projects = select(ProjectRow.id).where(ProjectRow.user_id == owner)
        key = await self.session.scalar(
            update(DraftRow)
            .where(DraftRow.id == identifier, DraftRow.project_id.in_(owned_projects))
            .values(
                draft_document=document_to_wire(document),
                client_material_language=metadata.language,
                change_order_labels=dict(metadata.labels.values)
                if isinstance(metadata.labels, Labels)
                else None,
                updated_at=now,
            )
            .returning(DraftRow.id)
        )
        return await self.load_owned(owner, identifier) if key else None


class DraftUnitOfWork:
    def __init__(self, work: SqlAlchemyUnitOfWork):
        self.work = work
        self.drafts: DraftRepository

    async def __aenter__(self) -> Self:
        await self.work.__aenter__()
        self.drafts = DraftRepository(self.work.session)
        return self

    async def commit(self) -> None:
        await self.work.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.work.__aexit__(exc_type, exc, traceback)
