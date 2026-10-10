from typing import Literal
from uuid import UUID

from pydantic import StrictStr, field_validator, model_validator

from scope_guard.core.contracts import EvaluationAccuracy, Verdict, WireModel


class EvaluationLabelRequest(WireModel):
    history_entry_id: UUID
    accuracy: EvaluationAccuracy
    ai_reasoning: StrictStr
    human_verdict: Verdict | None = None

    @field_validator("ai_reasoning")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("reasoning_required")
        return value.strip()

    @model_validator(mode="after")
    def verdict_presence(self):
        if self.accuracy == EvaluationAccuracy.wrong:
            if self.human_verdict is None:
                raise ValueError("human_verdict_required")
        elif "human_verdict" in self.model_fields_set:
            raise ValueError("human_verdict_prohibited")
        return self


class EvaluationResponse(WireModel):
    id: UUID
    accuracy: EvaluationAccuracy
    human_verdict: Verdict | None


class EvaluationJsonlRecord(WireModel):
    # This export deliberately uses snake_case instead of the business API convention.
    scope: StrictStr
    request: StrictStr
    ai_verdict: Literal["IN_SCOPE", "BORDERLINE", "OUT_OF_SCOPE"]
    human_verdict: Literal["IN_SCOPE", "BORDERLINE", "OUT_OF_SCOPE"] | None
    ai_reasoning: StrictStr
    project_type: Literal["development", "design", "marketing"]

    def to_wire(self):
        return self.model_dump(mode="json", by_alias=False)
