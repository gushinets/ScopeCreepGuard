"""Immutable project values, independent of HTTP JSON and database rows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from scope_guard.core.contracts import Currency, Industry, PricingModel, Verdict
from scope_guard.modules.projects.schemas import CreateProjectRequest


@dataclass(frozen=True)
class CommercialTerms:
    start_date: date
    pricing_model: PricingModel
    currency: Currency
    amount: Decimal

    def __post_init__(self):
        if not self.amount.is_finite() or not 0 < self.amount < Decimal("1e12"):
            raise ValueError("invalid_commercial_terms")
        if self.amount != self.amount.quantize(Decimal("0.01")):
            raise ValueError("invalid_commercial_terms")

    @classmethod
    def from_project_input(cls, card: CreateProjectRequest) -> "CommercialTerms":
        amount = card.hourly_rate if card.pricing_model == PricingModel.hourly else card.fixed_price
        if amount is None:
            raise ValueError("invalid_commercial_terms")
        return cls(card.start_date, card.pricing_model, card.currency, Decimal(amount))


@dataclass(frozen=True, slots=True)
class AgreedScope:
    text: str


@dataclass(frozen=True, slots=True)
class ProjectDate:
    # Lexical date preserves the legacy parser's acceptance of year zero.
    value: str


@dataclass(frozen=True, slots=True)
class ProjectDates:
    start: ProjectDate | None
    last_checked: date | None = None


@dataclass(frozen=True, slots=True)
class OptionalClient:
    value: str | None
    supplied: bool = True


@dataclass(frozen=True, slots=True)
class PricingConfiguration:
    model: PricingModel | None
    currency: Currency | None
    hourly_rate: Decimal | None
    fixed_price: Decimal | None


@dataclass(frozen=True, slots=True)
class ProjectCard:
    name: str
    scope: AgreedScope
    industry: Industry
    dates: ProjectDates
    pricing: PricingConfiguration
    client: OptionalClient


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    card: ProjectCard


@dataclass(frozen=True, slots=True)
class ProjectHistoryEntry:
    project_id: UUID
    id: UUID
    date: date
    request: str
    verdict: Verdict
    summary: str
    draft_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProjectDetail:
    project: Project
    history: tuple[ProjectHistoryEntry, ...] = ()
