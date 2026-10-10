from datetime import date
from typing import Self
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.infrastructure.database.models import DraftRow, HistoryEntryRow, ProjectRow
from scope_guard.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.modules.projects.domain import (
    AgreedScope,
    OptionalClient,
    PricingConfiguration,
    Project,
    ProjectCard,
    ProjectDate,
    ProjectDates,
    ProjectHistoryEntry,
)


def project(row: ProjectRow) -> Project:
    card = ProjectCard(
        name=row.name,
        scope=AgreedScope(row.scope),
        industry=row.industry,
        dates=ProjectDates(
            ProjectDate(row.start_date.isoformat()) if row.start_date else None,
            row.last_checked,
        ),
        pricing=PricingConfiguration(
            row.pricing_model,
            row.currency,
            row.hourly_rate,
            row.fixed_price,
        ),
        client=OptionalClient(row.client),
    )
    return Project(row.id, card)


def values(card: ProjectCard) -> dict:
    result = {
        "name": card.name,
        "scope": card.scope.text,
        "industry": card.industry,
        "start_date": date.fromisoformat(card.dates.start.value) if card.dates.start else None,
        "pricing_model": card.pricing.model,
        "currency": card.pricing.currency,
        "hourly_rate": card.pricing.hourly_rate,
        "fixed_price": card.pricing.fixed_price,
    }
    if card.client.supplied:
        result["client"] = card.client.value
    return result


class Projects:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_owned(self, owner: UUID) -> tuple[Project, ...]:
        rows = await self.session.scalars(
            select(ProjectRow)
            .where(ProjectRow.user_id == owner)
            .order_by(ProjectRow.created_at.desc())
        )
        return tuple(project(row) for row in rows)

    async def get_owned(self, owner: UUID, identifier: UUID) -> Project | None:
        row = await self.session.scalar(
            select(ProjectRow).where(ProjectRow.user_id == owner, ProjectRow.id == identifier)
        )
        return project(row) if row else None

    async def create(self, owner: UUID, card: ProjectCard) -> Project:
        row = ProjectRow(user_id=owner, **values(card))
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return project(row)

    async def update(self, owner: UUID, identifier: UUID, card: ProjectCard) -> Project | None:
        row = await self.session.scalar(
            update(ProjectRow)
            .where(ProjectRow.user_id == owner, ProjectRow.id == identifier)
            .values(**values(card))
            .returning(ProjectRow)
        )
        return project(row) if row else None

    async def delete(self, owner: UUID, identifier: UUID) -> bool:
        return (
            await self.session.scalar(
                delete(ProjectRow)
                .where(ProjectRow.user_id == owner, ProjectRow.id == identifier)
                .returning(ProjectRow.id)
            )
            is not None
        )


class History:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_projects(self, identifiers: tuple[UUID, ...]) -> tuple[ProjectHistoryEntry, ...]:
        if not identifiers:
            return ()
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


class ProjectUnitOfWork:
    def __init__(self, work: SqlAlchemyUnitOfWork):
        self.work = work
        self.projects: Projects
        self.history: History

    async def __aenter__(self) -> Self:
        await self.work.__aenter__()
        self.projects, self.history = Projects(self.work.session), History(self.work.session)
        return self

    async def commit(self) -> None:
        await self.work.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.work.__aexit__(exc_type, exc, traceback)
