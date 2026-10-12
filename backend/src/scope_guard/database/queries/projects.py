from datetime import date
from uuid import UUID

from sqlalchemy import select

from scope_guard.database.models import ProjectRow
from scope_guard.domain.projects.domain import (
    AgreedScope,
    OptionalClient,
    PricingConfiguration,
    Project,
    ProjectCard,
    ProjectDate,
    ProjectDates,
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


class ProjectQueries:
    def __init__(self, session):
        self.session = session

    async def list_owned(self, owner: UUID) -> tuple[Project, ...]:
        rows = await self.session.scalars(
            select(ProjectRow)
            .where(ProjectRow.user_id == owner)
            .order_by(ProjectRow.created_at.desc())
        )
        return tuple(project(row) for row in rows)


class ProjectReadWork:
    def __init__(self, work):
        self.work = work

    async def __aenter__(self):
        await self.work.__aenter__()
        self.projects = ProjectQueries(self.work.session)
        from scope_guard.database.queries.history import HistoryQueries

        self.history = HistoryQueries(self.work.session)
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.work.__aexit__(exc_type, exc, traceback)
