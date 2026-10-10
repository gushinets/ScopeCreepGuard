"""Allocate transport JSON from immutable project values; never return aliases."""

from decimal import Decimal

from scope_guard.modules.projects.domain import ProjectDetail, ProjectHistoryEntry


def amount(value: Decimal | None) -> str | None:
    return format(value, ".2f") if value is not None else None


def history_to_wire(entry: ProjectHistoryEntry) -> dict:
    result = {
        "id": str(entry.id),
        "date": entry.date.isoformat(),
        "request": entry.request,
        "verdict": entry.verdict.value,
        "summary": entry.summary,
    }
    if entry.draft_id is not None:
        result["draftId"] = str(entry.draft_id)
    return result


def project_to_wire(detail: ProjectDetail) -> dict:
    card = detail.project.card
    result = {
        "id": str(detail.project.id),
        "name": card.name,
        "clientName": card.client.value,
        "industry": card.industry.value,
        "scope": card.scope.text,
        "startDate": card.dates.start.value if card.dates.start else None,
        "pricingModel": card.pricing.model.value if card.pricing.model else None,
        "currency": card.pricing.currency.value if card.pricing.currency else None,
        "hourlyRate": amount(card.pricing.hourly_rate),
        "fixedPrice": amount(card.pricing.fixed_price),
        "history": [history_to_wire(entry) for entry in detail.history],
    }
    if card.dates.last_checked is not None:
        result["lastChecked"] = card.dates.last_checked.isoformat()
    return result
