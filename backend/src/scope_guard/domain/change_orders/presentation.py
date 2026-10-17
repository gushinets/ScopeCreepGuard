"""Effective commercial fields; editable and historical source values stay intact."""

from dataclasses import dataclass

from scope_guard.domain.drafts.values import EditableChangeOrder, thaw_json
from scope_guard.domain.shared.js_compat import js_string


@dataclass(frozen=True, slots=True)
class CommercialPresentation:
    no_charge: bool
    effort: str
    amount: str
    currency: str
    rationale: str
    schedule: str


def commercial_presentation(draft: EditableChangeOrder) -> CommercialPresentation:
    return CommercialPresentation(
        no_charge=draft.no_additional_charge,
        effort=draft.estimated_hours.strip(),
        amount="" if draft.no_additional_charge else draft.additional_cost.strip(),
        currency="" if draft.no_additional_charge else js_string(thaw_json(draft.currency)),
        rationale="" if draft.no_additional_charge else draft.rationale.strip(),
        schedule=draft.timeline_impact.strip(),
    )
