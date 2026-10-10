"""Existing commercial inputs only; estimation remains model-driven."""

from datetime import date

from scope_guard.core.js_compat import stringify
from scope_guard.modules.analysis.domain import GenerationContext


def calendar_day(value: str) -> int:
    year, month, day = map(int, value.split("-"))
    # JavaScript Date.UTC treats years 0..99 as 1900..1999.
    return date(year + 1900 if 0 <= year <= 99 else year, month, 1).toordinal() + day - 1


def project_timing(start: str, end: str | None, created: str) -> dict:
    creation = created[:10]
    boundary = end or creation
    return {
        "calculationEndDate": boundary,
        "endDateSource": "explicit" if end else "draft",
        "durationDays": calendar_day(boundary) - calendar_day(start),
        "elapsedDays": calendar_day(creation) - calendar_day(start),
    }


def commercial_signature(context: GenerationContext, end: str | None = None) -> str:
    return stringify(
        [
            context.pricing_model,
            context.currency,
            context.hourly_rate,
            context.fixed_price,
            context.start_date,
            end or "",
        ]
    )
