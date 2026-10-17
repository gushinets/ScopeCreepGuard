import re
from decimal import Decimal

from scope_guard.domain.change_orders.presentation import commercial_presentation
from scope_guard.domain.change_orders.readiness import document_readiness, readiness_message
from scope_guard.domain.drafts.values import EditableChangeOrder, JsonValue, thaw_json
from scope_guard.services.documents.models import PreparedDocument, Row
from scope_guard.services.documents.ports import DocumentLocalization


def money_value(value: str) -> Decimal | None:
    """Interpret numeric edits exactly; never quantize or replace the original text."""
    return Decimal(value) if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) else None


def prepare_document(
    draft: EditableChangeOrder,
    project_snapshot: JsonValue = None,
    *,
    localization: DocumentLocalization,
) -> PreparedDocument:
    language = localization.supported_language(draft.language)
    base = language.split("-")[0]
    labels = localization.document_labels(language, draft.labels)
    metadata = [Row(labels["project"], draft.project_name.strip())]
    issues = document_readiness(
        {
            "providerName": draft.provider_name,
            "clientName": draft.client_name,
            "description": draft.description,
            "estimatedHours": draft.estimated_hours,
            "additionalCost": draft.additional_cost,
            "currency": thaw_json(draft.currency),
            "timelineImpact": draft.timeline_impact,
            "endDate": draft.end_date,
            "noAdditionalCharge": draft.no_additional_charge,
        }
    )
    if issues:
        metadata.append(Row(labels["status"], readiness_message(issues, language, labels)))
    for key, value in [
        ("provider", draft.provider_name),
        ("client", draft.client_name),
        ("email", draft.client_email),
    ]:
        if value.strip():
            metadata.append(Row(labels[key], value.strip()))
    hours = {"ru": "ч", "es": "horas", "en": "hours"}.get(base, labels.get("hours", ""))
    # The editor's text is authoritative, including nonnumeric user overrides.
    terms = commercial_presentation(draft)
    cost = terms.amount
    money_value(cost)
    currency = terms.currency
    commercial = (
        Row(
            labels["effort"],
            f"{terms.effort} {hours}" if terms.effort else "—",
        ),
        Row(
            labels["fee"],
            labels["noCharge"]
            if terms.no_charge
            else f"{cost}{' ' + currency if currency else ''}"
            if cost
            else "—",
        ),
    )
    additional = []
    if terms.no_charge:
        additional.append(Row(labels["fee"], labels["outsideScopeFree"]))
    if draft.end_date:
        additional.append(
            Row(labels["endDate"], localization.document_date(draft.end_date, language))
        )
    for key, value in [
        ("terms", draft.additional_terms),
        ("rationale", terms.rationale),
        ("note", draft.note),
    ]:
        if value.strip():
            additional.append(Row(labels[key], value.strip()))
    reference = draft.reference.strip() if isinstance(draft.reference, str) else ""
    return PreparedDocument(
        tuple(labels.items()),
        reference or "CO-" + draft.created_at[:10].replace("-", ""),
        localization.document_date(draft.created_at, language),
        tuple(metadata),
        draft.description.strip(),
        commercial,
        terms.schedule,
        tuple(additional),
        (
            Row(labels["approvedBy"], draft.client_approver_name.strip()),
            Row(
                labels["date"],
                localization.document_date(draft.approval_date, language)
                if draft.approval_date
                else "",
            ),
        ),
        project_snapshot,
    )
