import calendar
import math
import re
from decimal import ROUND_HALF_UP, Decimal

from scope_guard.core.contracts import Currency, Industry, PricingModel
from scope_guard.modules.projects.domain import (
    AgreedScope,
    OptionalClient,
    PricingConfiguration,
    ProjectCard,
    ProjectDate,
    ProjectDates,
)
from scope_guard.modules.projects.use_cases import ProjectError

JS_SPACE = r"\x09-\x0d\x20\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def trim(value: str) -> str:
    return re.sub(rf"^[{JS_SPACE}]+|[{JS_SPACE}]+$", "", value)


def valid_date(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    year, month, day = map(int, value.split("-"))
    return 1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]


def money(value) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    raw = trim(str(value))
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", raw):
        return None
    try:
        amount = float(raw)
        if not math.isfinite(amount) or not 0 < amount < 1e12:
            return None
        # Number(...).toFixed(2) rounds the actual binary float, not the input decimal.
        return format(
            Decimal.from_float(amount).quantize(Decimal(".01"), rounding=ROUND_HALF_UP), ".2f"
        )
    except (ValueError, OverflowError):
        return None


def parse_project(body: dict) -> ProjectCard:
    for field, code in (("name", "projectNameRequired"), ("scope", "scopeRequired")):
        if not isinstance(body.get(field), str) or not trim(body[field]):
            raise ProjectError(code)
    if body.get("industry") not in ("Development", "Design", "Marketing"):
        raise ProjectError("industryInvalid")
    if not valid_date(body.get("startDate")):
        raise ProjectError("startDateInvalid")
    pricing = body.get("pricingModel")
    if pricing not in ("hourly", "fixed"):
        raise ProjectError("pricingModelInvalid")
    if body.get("currency") not in ("RUB", "USD", "EUR"):
        raise ProjectError("currencyInvalid")
    if (
        "clientName" in body
        and body["clientName"] is not None
        and not isinstance(body["clientName"], str)
    ):
        raise ProjectError("clientInvalid")
    amount = money(body.get("hourlyRate" if pricing == "hourly" else "fixedPrice"))
    if amount is None:
        raise ProjectError("hourlyRateInvalid" if pricing == "hourly" else "fixedPriceInvalid")
    return ProjectCard(
        name=trim(body["name"]),
        scope=AgreedScope(trim(body["scope"])),
        industry=Industry(body["industry"]),
        dates=ProjectDates(ProjectDate(body["startDate"])),
        pricing=PricingConfiguration(
            model=PricingModel(pricing),
            currency=Currency(body["currency"]),
            hourly_rate=Decimal(amount) if pricing == "hourly" else None,
            fixed_price=Decimal(amount) if pricing == "fixed" else None,
        ),
        client=OptionalClient(
            trim(body["clientName"]) if isinstance(body.get("clientName"), str) else None,
            supplied="clientName" in body,
        ),
    )
