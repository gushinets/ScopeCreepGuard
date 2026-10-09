import json
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import StrictStr, field_serializer, field_validator, model_validator

from scope_guard.core.contracts import Currency, Industry, PricingModel, Text, Verdict, WireModel
from scope_guard.modules.analysis.schemas import AnalysisSnapshot
from scope_guard.modules.change_orders.schemas import ClientMaterials, EditableChangeOrder, Replies


class ProjectSnapshot(WireModel):
    version: Literal[1]
    name: StrictStr
    client_name: StrictStr | None = None
    industry: Industry
    scope: StrictStr
    start_date: date | None
    end_date: StrictStr | None
    pricing_model: PricingModel | None
    currency: Currency | None
    hourly_rate: StrictStr | None
    fixed_price: StrictStr | None
    document_language: StrictStr | None


class ProjectDetails(WireModel):
    client_name: Text
    client_email: Text
    end_date: Text


class ReplyDocument(WireModel):
    tone: Literal["warm", "neutral", "firm"]
    text: Text
    generated: Replies


def check_size(value):
    if isinstance(value, dict):
        size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if size > 1_000_000:
            raise ValueError("draft_too_large")
    return value


class DraftDocument(WireModel):
    version: Literal[1]
    result: AnalysisSnapshot
    client_materials: ClientMaterials | None
    change_order: EditableChangeOrder | None
    reply: ReplyDocument
    project_details: ProjectDetails

    @model_validator(mode="before")
    @classmethod
    def size_limit(cls, value):
        return check_size(value)


class CreateDraftRequest(WireModel):
    project_id: UUID
    request: Text
    locale: Literal["en", "ru"]
    idempotency_key: UUID
    proof: StrictStr
    draft_document: DraftDocument

    @field_validator("request")
    @classmethod
    def nonblank_request(cls, value):
        if not value.strip():
            raise ValueError("required_text")
        return value.strip()

    @model_validator(mode="before")
    @classmethod
    def size_limit(cls, value):
        return check_size(value)


class UpdateDraftRequest(WireModel):
    draft_document: DraftDocument


class DraftResponse(WireModel):
    id: UUID
    project_id: UUID
    history_entry_id: UUID
    request: StrictStr
    created_at: datetime
    updated_at: datetime
    status: Literal["draft"]
    locale: Literal["en", "ru"]
    request_language: Literal["ru", "en", "es", "other"] | None
    client_material_language: StrictStr
    project_snapshot: ProjectSnapshot | None
    analysis_snapshot: AnalysisSnapshot
    draft_document: DraftDocument

    @field_serializer("created_at", "updated_at")
    def utc_timestamp(self, value):
        from datetime import UTC

        if value.tzinfo is None:
            raise ValueError("timezone_required")
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class DraftListItem(WireModel):
    id: UUID
    request_preview: StrictStr
    project_name: StrictStr
    verdict: Verdict
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def utc_timestamp(self, value):
        return DraftResponse.utc_timestamp(self, value)
