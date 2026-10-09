from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from scope_guard.core.contracts import Currency, PricingModel
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
