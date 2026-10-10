"""Public body shapes; per-route parsers retain error precedence and workflow validation.

These models are not installed as FastAPI body dependencies before authentication.
Opaque proof/document envelopes must be checked in the existing order by use cases.
"""

from datetime import date
from typing import Any, Literal

from pydantic import ConfigDict, StrictStr, field_validator, model_validator

from scope_guard.core.contracts import Verdict, WireModel, iso_date
from scope_guard.modules.evaluations.schemas import EvaluationLabelRequest
from scope_guard.modules.projects.schemas import CreateProjectRequest

PUBLIC_CONFIG = ConfigDict(populate_by_name=False, validate_by_name=False)


class PublicBody(WireModel):
    model_config = PUBLIC_CONFIG


class CredentialsBody(PublicBody):
    email: StrictStr
    password: StrictStr


class ProjectBody(CreateProjectRequest):
    model_config = PUBLIC_CONFIG

    @model_validator(mode="before")
    @classmethod
    def normalize_amounts(cls, value):
        if isinstance(value, dict):
            # Drop internal names before the domain model's normalization can copy them.
            value = {
                key: child
                for key, child in value.items()
                if key
                not in {name for name, field in cls.model_fields.items() if field.alias != name}
            }
        return super().normalize_amounts(value)


class ProjectUpdateBody(ProjectBody):
    """PATCH still replaces the full card; client-name presence remains visible."""


class AnalyzeBody(PublicBody):
    project_id: StrictStr
    request: StrictStr
    end_date: date | None = None
    document_language: StrictStr | None = None

    @field_validator("end_date", mode="before")
    @classmethod
    def wire_date(cls, value):
        if not isinstance(value, str):
            raise ValueError("invalid_date")
        return iso_date(value)


class ReplyBody(AnalyzeBody):
    tone: Literal["warm", "neutral", "firm"]
    previous_reply: StrictStr


class HistoricalBody(AnalyzeBody):
    history_id: StrictStr | None = None
    draft_id: StrictStr | None = None
    proof: StrictStr | None = None
    locale: Literal["en", "ru"] | None = None


class MaterialsBody(HistoricalBody):
    client_language: StrictStr
    analysis: dict[str, Any]


class CreateDraftBody(PublicBody):
    project_id: StrictStr
    request: StrictStr
    locale: Literal["en", "ru"]
    idempotency_key: StrictStr
    proof: StrictStr
    draft_document: dict[str, Any]


class UpdateDraftBody(PublicBody):
    draft_document: dict[str, Any]


class HistoryBody(PublicBody):
    date: StrictStr
    request: StrictStr
    verdict: Verdict
    summary: StrictStr


class EvaluationBody(EvaluationLabelRequest):
    model_config = PUBLIC_CONFIG


class LocaleBody(PublicBody):
    locale: Literal["en", "ru"]


REQUEST_MODELS = {
    "POST /api/auth/register": CredentialsBody,
    "POST /api/auth/login": CredentialsBody,
    "POST /api/projects": ProjectBody,
    "PATCH /api/projects/{id}": ProjectUpdateBody,
    "POST /api/projects/{id}/history": HistoryBody,
    "POST /api/analyze": AnalyzeBody,
    "POST /api/replies/regenerate": ReplyBody,
    "POST /api/client-materials/language": MaterialsBody,
    "POST /api/change-orders/estimate": HistoricalBody,
    "POST /api/drafts": CreateDraftBody,
    "PUT /api/drafts/{draftId}": UpdateDraftBody,
    "POST /api/evaluations": EvaluationBody,
    "POST /api/locale": LocaleBody,
}
