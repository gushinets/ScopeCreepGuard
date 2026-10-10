"""Detached draft values; legacy JSON is retained without read normalization."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from scope_guard.modules.analysis.domain import (
    ABSENT,
    Absent,
    AnalysisResult,
    ClientMaterials,
    Labels,
    Replies,
)


@dataclass(frozen=True, slots=True)
class JsonObject:
    entries: tuple[tuple[str, "JsonValue"], ...]

    def get(self, key: str) -> "JsonValue | Absent":
        return next((value for name, value in self.entries if name == key), ABSENT)


@dataclass(frozen=True, slots=True)
class JsonArray:
    items: tuple["JsonValue", ...]


type JsonValue = JsonObject | JsonArray | str | int | float | bool | None


def freeze_json(value: object) -> JsonValue:
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("invalid_json_key")
        return JsonObject(tuple((key, freeze_json(child)) for key, child in value.items()))
    if isinstance(value, list):
        return JsonArray(tuple(freeze_json(child) for child in value))
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError("invalid_json_value")


def freeze_object(value: object) -> JsonObject:
    result = freeze_json(value)
    if not isinstance(result, JsonObject):
        raise ValueError("invalid_json_object")
    return result


def thaw_json(value: JsonValue):
    if isinstance(value, JsonObject):
        return {name: thaw_json(child) for name, child in value.entries}
    if isinstance(value, JsonArray):
        return [thaw_json(child) for child in value.items]
    return value


@dataclass(frozen=True, slots=True)
class EditableChangeOrder:
    created_at: str
    project_name: str
    description: str
    estimated_hours: str
    additional_cost: str
    timeline_impact: str
    rationale: str
    note: str
    provider_name: str
    client_name: str
    client_email: str
    end_date: str
    additional_terms: str
    client_approver_name: str
    approval_date: str
    language: str
    currency: JsonValue
    no_additional_charge: bool
    reference: str | Absent = ABSENT
    labels: Labels | Absent = ABSENT
    ai_values: tuple[tuple[str, str], ...] | Absent = ABSENT


@dataclass(frozen=True, slots=True)
class ReplyDocument:
    tone: JsonValue
    text: str
    generated: Replies


@dataclass(frozen=True, slots=True)
class ProjectDetails:
    client_name: str
    client_email: str
    end_date: str


@dataclass(frozen=True, slots=True)
class DraftDocument:
    result: AnalysisResult
    client_materials: ClientMaterials | None
    change_order: EditableChangeOrder | None
    reply: ReplyDocument
    project_details: ProjectDetails


@dataclass(frozen=True, slots=True)
class CreateDraft:
    project_id: UUID
    idempotency_key: UUID
    request: str
    locale: str
    analysis_snapshot: JsonObject
    project_snapshot: JsonObject
    document: DraftDocument


@dataclass(frozen=True, slots=True)
class StoredDraft:
    id: UUID
    project_id: UUID
    history_entry_id: UUID
    request: str
    created_at: datetime
    updated_at: datetime
    locale: str
    request_language: str | None
    client_material_language: str
    project_snapshot: JsonValue
    analysis_snapshot: JsonObject
    document: JsonObject


@dataclass(frozen=True, slots=True)
class DraftSummary:
    id: UUID
    request: str
    project_name: str
    verdict: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DraftHistory:
    id: UUID
    project_id: UUID
    date: date
    request: str
    verdict: str
    summary: str
    draft_id: UUID


@dataclass(frozen=True, slots=True)
class CreatedDraft:
    draft: StoredDraft
    entry: DraftHistory
    created: bool


@dataclass(frozen=True, slots=True)
class LanguageMetadata:
    language: str
    labels: Labels | Absent


def language_metadata(document: DraftDocument) -> LanguageMetadata:
    material, co, result = document.client_materials, document.change_order, document.result
    return LanguageMetadata(
        material.client_language
        if material
        else result.client_language or (co.language if co else "en"),
        co.labels
        if co and co.labels != ABSENT
        else material.change_order_labels
        if material and material.change_order_labels != ABSENT
        else result.change_order_labels,
    )
