"""HTTP envelopes. Business models and repositories do not depend on transport."""

from typing import Literal
from uuid import UUID

from pydantic import StrictStr

from scope_guard.api.errors import ErrorCode
from scope_guard.core.contracts import WireModel
from scope_guard.modules.analysis.schemas import AnalysisSnapshot
from scope_guard.modules.auth.schemas import UserResponse
from scope_guard.modules.change_orders.schemas import ClientMaterials
from scope_guard.modules.drafts.schemas import DraftListItem, DraftResponse, ProjectSnapshot
from scope_guard.modules.evaluations.schemas import EvaluationJsonlRecord, EvaluationResponse
from scope_guard.modules.projects.schemas import HistoryEntryResponse, ProjectResponse


class ErrorResponse(WireModel):
    error: ErrorCode


class OkResponse(WireModel):
    ok: Literal[True]


class AuthResponse(WireModel):
    user: UserResponse


class ProjectEnvelope(WireModel):
    project: ProjectResponse

    def to_wire(self):
        return {"project": self.project.to_wire()}


class ProjectsResponse(WireModel):
    projects: list[ProjectResponse]

    def to_wire(self):
        return {"projects": [project.to_wire() for project in self.projects]}


class HistoryResponse(WireModel):
    entry: HistoryEntryResponse

    def to_wire(self):
        return {"entry": self.entry.to_wire()}


class AnalyzeResponse(WireModel):
    result: AnalysisSnapshot
    project_snapshot: ProjectSnapshot
    proof: StrictStr


class ReplyResponse(WireModel):
    reply: StrictStr


class MaterialsResponse(WireModel):
    materials: ClientMaterials


class EstimateResponse(WireModel):
    result: AnalysisSnapshot


class CreatedHistoryEntry(HistoryEntryResponse):
    project_id: UUID


class DraftEnvelope(WireModel):
    draft: DraftResponse


class CreatedDraftResponse(DraftEnvelope):
    entry: CreatedHistoryEntry


class DraftsResponse(WireModel):
    drafts: list[DraftListItem]


class EvaluationEnvelope(WireModel):
    evaluation: EvaluationResponse


# Export is a sequence of records, not a JSON envelope; registered for coverage.
RESPONSE_MODELS = {
    "POST /api/auth/register": AuthResponse,
    "POST /api/auth/login": AuthResponse,
    "GET /api/auth/me": AuthResponse,
    "POST /api/auth/logout": OkResponse,
    "GET /api/projects": ProjectsResponse,
    "POST /api/projects": ProjectEnvelope,
    "GET /api/projects/{id}": ProjectEnvelope,
    "PATCH /api/projects/{id}": ProjectEnvelope,
    "DELETE /api/projects/{id}": OkResponse,
    "POST /api/projects/{id}/history": HistoryResponse,
    "POST /api/analyze": AnalyzeResponse,
    "POST /api/replies/regenerate": ReplyResponse,
    "POST /api/client-materials/language": MaterialsResponse,
    "POST /api/change-orders/estimate": EstimateResponse,
    "POST /api/drafts": CreatedDraftResponse,
    "GET /api/drafts": DraftsResponse,
    "GET /api/drafts/{draftId}": DraftEnvelope,
    "PUT /api/drafts/{draftId}": DraftEnvelope,
    "POST /api/evaluations": EvaluationEnvelope,
    "GET /api/evaluations/export": EvaluationJsonlRecord,
    "POST /api/locale": OkResponse,
}
