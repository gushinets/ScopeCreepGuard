from datetime import date
from uuid import UUID

from sqlalchemy import select

from scope_guard.database.models import DraftRow, HistoryEntryRow, ProjectRow
from scope_guard.domain.projects.domain import (
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


class HistoryQueries:
    def __init__(self, session):
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
