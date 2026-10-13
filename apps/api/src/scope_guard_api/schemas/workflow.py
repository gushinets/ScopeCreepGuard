"""Versioned workflow DTOs. These are not database mappings."""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StrictBool, StrictInt, StrictStr

from scope_guard_api.schemas.analysis import AnalysisSnapshot
from scope_guard_api.schemas.drafts import DraftEditableChangeOrder
from scope_guard_api.schemas.shared import WireModel

Revision = Annotated[StrictStr, Field(pattern=r"^[1-9][0-9]*$", max_length=19)]


class InputModel(WireModel):
    model_config = ConfigDict(
        alias_generator=WireModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )


class Operation(InputModel):
    operation_id: UUID


class VersionedOperation(Operation):
    expected_revision: Revision


class ReplyAlternatives(InputModel):
    warm: StrictStr
    neutral: StrictStr
    firm: StrictStr


class WorkingReply(InputModel):
    text: StrictStr
    tone: Literal["warm", "neutral", "firm"]
    language: StrictStr
    generated: ReplyAlternatives


class EstimateProvenance(InputModel):
    analysis_run_id: UUID
    source_draft_revision: Revision
    effective_end_date: date | None
    commercial_signature: StrictStr
    estimate_valid: StrictBool


class WorkingDocument(InputModel):
    version: Literal[2]
    reply: WorkingReply
    change_order: DraftEditableChangeOrder | None
    estimate: EstimateProvenance | None = None
    language_selection: dict[str, Any] | None = None


class WorkingChanges(InputModel):
    request_text: Annotated[StrictStr, Field(max_length=100_000)] | None = None
    draft_document: WorkingDocument | None = None


class SaveWorkingDraft(VersionedOperation):
    changes: WorkingChanges
    reason: Literal[
        "autosave", "manual_save", "tone_change", "language_change", "change_order_edit"
    ] = "autosave"


class RunAnalysis(VersionedOperation):
    locale: Literal["en", "ru"]
    document_language: StrictStr | None = None


class TranslateWorkingDraft(VersionedOperation):
    language: StrictStr


class ProjectWrite(Operation):
    name: StrictStr
    client_name: StrictStr | None = None
    client_email: StrictStr | None = None
    industry: Literal["Development", "Design", "Marketing"]
    scope: StrictStr
    start_date: StrictStr
    end_date: StrictStr | None = None
    pricing_model: Literal["hourly", "fixed"]
    currency: Literal["RUB", "USD", "EUR"]
    hourly_rate: StrictStr | StrictInt | None = None
    fixed_price: StrictStr | StrictInt | None = None


class ProjectUpdate(ProjectWrite):
    expected_revision: Revision


class WorkflowProject(WireModel):
    id: UUID
    name: str
    client_name: str | None = None
    client_email: str | None = None
    industry: str
    scope: str
    start_date: str | None = None
    end_date: str | None = None
    pricing_model: str | None = None
    currency: str | None = None
    hourly_rate: str | None = None
    fixed_price: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    last_checked: str | None = None
    history: list[dict[str, Any]] = []


class AnalysisRunDTO(WireModel):
    id: UUID
    project_id: UUID
    source_draft_id: UUID
    source_draft_revision: Revision
    request_text: str
    project_snapshot: dict[str, Any]
    interface_locale: str
    requested_document_language: str | None = None
    request_language: str | None = None
    result_snapshot: AnalysisSnapshot | None = None
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"]
    purpose: Literal["analysis", "estimate"] = "analysis"
    model: str | None = None
    prompt_version: str | None = None
    error_code: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkingDraftDTO(WireModel):
    id: UUID
    project_id: UUID
    request_text: str
    last_analysis_run_id: UUID | None
    analysis_is_stale: bool
    draft_document: WorkingDocument
    revision: Revision
    created_at: datetime
    updated_at: datetime
    analysis_run: AnalysisRunDTO | None = None


class DraftResponse(WireModel):
    draft: WorkingDraftDTO


class ProjectResponse(WireModel):
    project: WorkflowProject


class ProjectsResponse(WireModel):
    projects: list[WorkflowProject]


class AnalysisResponse(WireModel):
    analysis_run: AnalysisRunDTO
    draft: WorkingDraftDTO | None
    applied: bool
    conflict: bool = False
    history_entry_id: UUID | None = None


class PendingLlmOperation(WireModel):
    operation_id: UUID
    status: Literal["queued", "running", "succeeded", "failed"]
    status_url: str
    deadline_at: datetime


class LlmOperationStatus(PendingLlmOperation):
    stages: dict[str, str]
    response_format: str
    result: dict[str, Any] | None
    error: dict[str, Any] | None


class Feedback(InputModel):
    accuracy: Literal["correct", "wrong", "debatable"]
    human_verdict: Literal["in_scope", "borderline", "out_of_scope"] | None = None


class ExportRequest(Operation):
    language: StrictStr | None = None


class HistoryEntryDTO(WireModel):
    id: UUID
    project_id: UUID
    source_draft_id: UUID | None
    source_draft_revision: Revision | None
    analysis_run_id: UUID | None
    check_snapshot: dict[str, Any]
    schema_version: int
    verdict: Literal["in_scope", "borderline", "out_of_scope"]
    summary: str
    request: str
    date: str
    completed_at: datetime | None
    saved_by_user_id: UUID | None
    source_kind: Literal["explicit", "legacy_unverified"]


class HistoryResponse(WireModel):
    entry: HistoryEntryDTO


class HistoriesResponse(WireModel):
    entries: list[HistoryEntryDTO]


class AgreementDTO(WireModel):
    id: UUID
    project_id: UUID
    history_entry_id: UUID
    reference: str
    content_snapshot: dict[str, Any]
    schema_version: int
    status: Literal["finalized", "voided"]
    revision: Revision
    finalized_by_user_id: UUID
    finalized_at: datetime
    voided_at: datetime | None
    updated_at: datetime


class AgreementResponse(WireModel):
    change_order: AgreementDTO


class AgreementsResponse(WireModel):
    change_orders: list[AgreementDTO]


class ExportDTO(WireModel):
    id: UUID
    change_order_id: UUID
    format: Literal["pdf"]
    language: str
    renderer_version: str
    template_version: str
    status: Literal["pending", "processing", "ready", "failed", "expired"]
    checksum: str | None
    mime_type: str | None
    size_bytes: int | None
    error_code: str | None
    attempt_count: int
    created_at: datetime
    finished_at: datetime | None


class ExportResponse(WireModel):
    export: ExportDTO


class ExportsResponse(WireModel):
    exports: list[ExportDTO]


class RevisionDTO(WireModel):
    id: UUID
    draft_id: UUID
    revision: Revision
    state_snapshot: dict[str, Any]
    schema_version: int
    reason: str
    actor_type: str
    actor_user_id: UUID | None
    created_at: datetime
    project_id: UUID | None = None


class RevisionResponse(WireModel):
    revision: RevisionDTO


class RevisionsResponse(WireModel):
    revisions: list[RevisionDTO]
