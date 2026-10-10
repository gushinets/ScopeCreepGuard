from dataclasses import dataclass, replace

from scope_guard.modules.analysis.domain import FrozenObject, GenerationContext, thaw


@dataclass(frozen=True, slots=True)
class HistoricalGenerationDraft:
    project_id: str
    request: str
    project_snapshot: FrozenObject | None
    display_project_name: str
    display_client_name: str


@dataclass(frozen=True, slots=True)
class ProjectSnapshotOverlay:
    fields: FrozenObject


def overlay(
    current: GenerationContext, snapshot: FrozenObject, client: object
) -> GenerationContext:
    raw = thaw(snapshot)
    mapping = {
        "name": "name",
        "industry": "industry",
        "scope": "scope",
        "startDate": "start_date",
        "pricingModel": "pricing_model",
        "currency": "currency",
        "hourlyRate": "hourly_rate",
        "fixedPrice": "fixed_price",
    }
    values = {field: raw[key] for key, field in mapping.items() if key in raw}
    values["client_name"] = client
    return replace(current, **values)


def from_draft(current: GenerationContext, draft: HistoricalGenerationDraft) -> GenerationContext:
    if draft.project_snapshot is None:
        return replace(
            current,
            name=draft.display_project_name,
            client_name=draft.display_client_name,
            scope="",
            start_date=None,
            pricing_model=None,
            currency=None,
            hourly_rate=None,
            fixed_price=None,
        )
    raw = thaw(draft.project_snapshot)
    return overlay(
        current, draft.project_snapshot, raw.get("clientName", draft.display_client_name)
    )
