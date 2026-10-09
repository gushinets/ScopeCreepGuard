from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from scope_guard.core.contracts import Currency, Verdict, WireModel, language_tag
from scope_guard.modules.change_orders.schemas import ChangeOrderLabels, Replies


class AnalysisChangeOrder(WireModel):
    description: StrictStr
    timeline_impact: StrictStr
    additional_cost: StrictStr
    note: StrictStr
    estimated_hours: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] | None = None
    currency: Currency | Literal[""] | None = None
    rationale: StrictStr | None = None

    @field_validator("description", "timeline_impact", "additional_cost", "note")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("empty_analysis_text")
        return value.strip()


class AnalysisSnapshot(WireModel):
    verdict: Verdict
    confidence: Annotated[StrictInt, Field(ge=0, le=100)]
    summary: StrictStr
    reasoning: StrictStr
    citations: list[StrictStr]
    suggestion: StrictStr | None = None
    replies: Replies
    change_order: AnalysisChangeOrder
    has_additional_work: StrictBool | None = None
    request_language: Literal["ru", "en", "es", "other"] | None = None
    client_language: StrictStr | None = None
    change_order_labels: ChangeOrderLabels | None = None
    draft_created_at: StrictStr | None = None
    commercial_signature: StrictStr | None = None
    estimate_valid: StrictBool | None = None

    @field_validator("summary", "reasoning")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("empty_analysis_text")
        return value.strip()

    @field_validator("client_language")
    @classmethod
    def tag(cls, value):
        return language_tag(value) if value is not None else value

    @field_validator("draft_created_at")
    @classmethod
    def timestamp(cls, value):
        if value is not None:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def validate_replies_and_labels(self):
        if any(not value.strip() for value in self.replies.model_dump().values()):
            raise ValueError("empty_reply")
        if (
            self.client_language
            and self.client_language.split("-")[0] not in {"ru", "en", "es"}
            and not self.change_order_labels
        ):
            raise ValueError("labels_required")
        return self
