import re
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import StrictStr, field_validator, model_validator

from scope_guard.core.contracts import (
    Currency,
    Industry,
    PricingModel,
    Verdict,
    WireModel,
    iso_date,
)


def money(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("invalid_money")
    raw = str(value).strip()
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", raw):
        raise ValueError("invalid_money")
    amount = Decimal(raw)
    if not 0 < amount < Decimal("1000000000000"):
        raise ValueError("invalid_money")
    return format(amount, ".2f")


class CreateProjectRequest(WireModel):
    name: StrictStr
    client_name: StrictStr | None = None
    industry: Industry
    scope: StrictStr
    start_date: date
    pricing_model: PricingModel
    currency: Currency
    hourly_rate: StrictStr | None = None
    fixed_price: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_amounts(cls, value):
        if not isinstance(value, dict):
            return value
        result = dict(value)
        pricing = result.get("pricingModel", result.get("pricing_model"))
        if pricing not in {"hourly", "fixed"}:
            return result
        active = "hourlyRate" if pricing == "hourly" else "fixedPrice"
        snake = "hourly_rate" if pricing == "hourly" else "fixed_price"
        result[active] = money(result.get(active, result.get(snake)))
        result["fixedPrice" if pricing == "hourly" else "hourlyRate"] = None
        return result

    @field_validator("name", "scope")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("required_text")
        return value.strip()

    @field_validator("client_name")
    @classmethod
    def trim_client(cls, value):
        return value.strip() if value is not None else None

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_date(cls, value):
        return iso_date(value)


class UpdateProjectRequest(CreateProjectRequest):
    """The existing PATCH replaces the full card, not arbitrary partial fields."""


class HistoryEntryResponse(WireModel):
    id: UUID
    draft_id: UUID | None = None
    date: date
    request: StrictStr
    verdict: Verdict
    summary: StrictStr

    def to_wire(self):
        result = super().to_wire()
        if self.draft_id is None:
            result.pop("draftId", None)
        return result


class ProjectResponse(WireModel):
    id: UUID
    name: StrictStr
    client_name: StrictStr | None = None
    industry: Industry
    scope: StrictStr
    start_date: date | None
    pricing_model: PricingModel | None
    currency: Currency | None
    hourly_rate: StrictStr | None
    fixed_price: StrictStr | None
    last_checked: date | None = None
    history: list[HistoryEntryResponse]

    @field_validator("hourly_rate", "fixed_price", mode="before")
    @classmethod
    def decimal_string(cls, value):
        return format(value, ".2f") if isinstance(value, Decimal) else value

    def to_wire(self):
        result = super().to_wire()
        if self.last_checked is None:
            result.pop("lastChecked", None)
        result["history"] = [entry.to_wire() for entry in self.history]
        return result
