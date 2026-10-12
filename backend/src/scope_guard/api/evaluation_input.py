import re
from uuid import UUID

from scope_guard.api.errors import ApiError, ErrorCode
from scope_guard.api.project_input import trim
from scope_guard.core.contracts import EvaluationAccuracy, Verdict
from scope_guard.domain.evaluations.domain import EvaluationLabel

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def parse_evaluation(body: dict) -> EvaluationLabel:
    history_id = body.get("historyEntryId")
    if not isinstance(history_id, str) or not UUID_PATTERN.fullmatch(history_id):
        raise ApiError(ErrorCode.evaluation_history_not_found, 404)
    reasoning = body.get("aiReasoning")
    if not isinstance(reasoning, str) or not trim(reasoning):
        raise ApiError(ErrorCode.evaluation_reasoning_required)
    accuracy = body.get("accuracy")
    if accuracy not in ("correct", "wrong", "debatable"):
        raise ApiError(ErrorCode.evaluation_label_invalid)
    present = "humanVerdict" in body
    human = body.get("humanVerdict")
    if accuracy == "wrong":
        if human not in ("in_scope", "borderline", "out_of_scope"):
            raise ApiError(ErrorCode.evaluation_label_invalid)
    elif present:
        raise ApiError(ErrorCode.evaluation_label_invalid)
    return EvaluationLabel(
        UUID(history_id),
        EvaluationAccuracy(accuracy),
        trim(reasoning),
        Verdict(str(human)) if accuracy == "wrong" else None,
    )
