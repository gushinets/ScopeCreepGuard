"""Fresh wire values, including JavaScript preview and UTC date semantics."""

from datetime import UTC, datetime

from scope_guard.core.js_compat import utf16_length
from scope_guard.modules.analysis.domain import ABSENT, Labels
from scope_guard.modules.analysis.serialization import (
    analysis_to_wire,
    materials_to_wire,
    replies_to_wire,
)
from scope_guard.modules.drafts.values import (
    CreatedDraft,
    DraftDocument,
    DraftSummary,
    StoredDraft,
    thaw_json,
)

EDITOR_FIELDS = (
    ("createdAt", "created_at"),
    ("projectName", "project_name"),
    ("description", "description"),
    ("estimatedHours", "estimated_hours"),
    ("additionalCost", "additional_cost"),
    ("timelineImpact", "timeline_impact"),
    ("rationale", "rationale"),
    ("note", "note"),
    ("providerName", "provider_name"),
    ("clientName", "client_name"),
    ("clientEmail", "client_email"),
    ("endDate", "end_date"),
    ("additionalTerms", "additional_terms"),
    ("clientApproverName", "client_approver_name"),
    ("approvalDate", "approval_date"),
)


def document_to_wire(document: DraftDocument) -> dict:
    co = document.change_order
    editor = None
    if co is not None:
        editor = {key: getattr(co, field) for key, field in EDITOR_FIELDS}
        editor.update(
            language=co.language,
            currency=thaw_json(co.currency),
            noAdditionalCharge=co.no_additional_charge,
        )
        if co.reference != ABSENT:
            editor["reference"] = co.reference
        if isinstance(co.labels, Labels):
            editor["changeOrderLabels"] = dict(co.labels.values)
        if isinstance(co.ai_values, tuple):
            editor["aiValues"] = dict(co.ai_values)
    details = document.project_details
    return {
        "version": 1,
        "result": analysis_to_wire(document.result),
        "clientMaterials": materials_to_wire(document.client_materials)
        if document.client_materials
        else None,
        "changeOrder": editor,
        "reply": {
            "tone": thaw_json(document.reply.tone),
            "text": document.reply.text,
            "generated": replies_to_wire(document.reply.generated),
        },
        "projectDetails": {
            "clientName": details.client_name,
            "clientEmail": details.client_email,
            "endDate": details.end_date,
        },
    }


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def request_preview(value: str) -> str:
    if utf16_length(value) <= 160:
        return value
    return (
        value.encode("utf-16-le", "surrogatepass")[:314].decode("utf-16-le", "surrogatepass") + "…"
    )


def draft_to_wire(value: StoredDraft) -> dict:
    return {
        "id": str(value.id),
        "projectId": str(value.project_id),
        "historyEntryId": str(value.history_entry_id),
        "request": value.request,
        "createdAt": timestamp(value.created_at),
        "updatedAt": timestamp(value.updated_at),
        "status": "draft",
        "locale": value.locale,
        "requestLanguage": value.request_language,
        "clientMaterialLanguage": value.client_material_language,
        "projectSnapshot": thaw_json(value.project_snapshot),
        "analysisSnapshot": thaw_json(value.analysis_snapshot),
        "draftDocument": thaw_json(value.document),
    }


def summary_to_wire(value: DraftSummary) -> dict:
    return {
        "id": str(value.id),
        "requestPreview": request_preview(value.request),
        "projectName": value.project_name,
        "verdict": value.verdict,
        "createdAt": timestamp(value.created_at),
        "updatedAt": timestamp(value.updated_at),
    }


def created_to_wire(value: CreatedDraft) -> dict:
    entry = value.entry
    return {
        "draft": draft_to_wire(value.draft),
        "entry": {
            "id": str(entry.id),
            "projectId": str(entry.project_id),
            "draftId": str(entry.draft_id),
            "date": entry.date.isoformat(),
            "request": entry.request,
            "verdict": entry.verdict,
            "summary": entry.summary,
        },
    }
