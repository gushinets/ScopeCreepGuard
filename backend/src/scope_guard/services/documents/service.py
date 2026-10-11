import re
from decimal import Decimal

from scope_guard.core.js_compat import js_string
from scope_guard.modules.drafts.values import EditableChangeOrder, JsonValue, thaw_json
from scope_guard.services.documents.localization import (
    document_date,
    document_labels,
    supported_language,
)
from scope_guard.services.documents.models import PreparedDocument, Row


def money_value(value: str) -> Decimal | None:
    """Interpret numeric edits exactly; never quantize or replace the original text."""
    return Decimal(value) if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) else None


def prepare_document(
    draft: EditableChangeOrder, project_snapshot: JsonValue = None
) -> PreparedDocument:
    language = supported_language(draft.language)
    base = language.split("-")[0]
    labels = document_labels(language, draft.labels)
    metadata = [Row(labels["project"], draft.project_name.strip())]
    for key, value in [
        ("provider", draft.provider_name),
        ("client", draft.client_name),
        ("email", draft.client_email),
    ]:
        if value.strip():
            metadata.append(Row(labels[key], value.strip()))
    hours = {"ru": "ч", "es": "horas", "en": "hours"}.get(base, labels.get("hours", ""))
    # The editor's text is authoritative, including nonnumeric user overrides.
    cost = draft.additional_cost.strip()
    money_value(cost)
    currency = js_string(thaw_json(draft.currency))
    commercial = (
        Row(
            labels["effort"],
            f"{draft.estimated_hours.strip()} {hours}" if draft.estimated_hours.strip() else "—",
        ),
        Row(
            labels["fee"],
            labels["noCharge"]
            if draft.no_additional_charge
            else f"{cost}{' ' + currency if currency else ''}"
            if cost
            else "—",
        ),
    )
    additional = []
    if draft.no_additional_charge:
        additional.append(Row(labels["fee"], labels["outsideScopeFree"]))
    if draft.end_date:
        additional.append(Row(labels["endDate"], document_date(draft.end_date, language)))
    for key, value in [
        ("terms", draft.additional_terms),
        ("rationale", draft.rationale),
        ("note", draft.note),
    ]:
        if value.strip():
            additional.append(Row(labels[key], value.strip()))
    reference = draft.reference.strip() if isinstance(draft.reference, str) else ""
    return PreparedDocument(
        tuple(labels.items()),
        reference or "CO-" + draft.created_at[:10].replace("-", ""),
        document_date(draft.created_at, language),
        tuple(metadata),
        draft.description.strip(),
        commercial,
        draft.timeline_impact.strip(),
        tuple(additional),
        (
            Row(labels["approvedBy"], draft.client_approver_name.strip()),
            Row(
                labels["date"],
                document_date(draft.approval_date, language) if draft.approval_date else "",
            ),
        ),
        project_snapshot,
    )
