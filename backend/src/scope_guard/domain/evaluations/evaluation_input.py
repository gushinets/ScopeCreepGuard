import re
from uuid import UUID

from scope_guard.domain.evaluations.domain import EvaluationLabel
from scope_guard.domain.shared.enums import EvaluationAccuracy, Verdict
from scope_guard.domain.shared.errors import ValidationError
from scope_guard.domain.shared.js_compat import trim

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def parse_evaluation(body: dict) -> EvaluationLabel:
    history_id = body.get("historyEntryId")
    if not isinstance(history_id, str) or not UUID_PATTERN.fullmatch(history_id):
        raise ValidationError("errors.evaluationHistoryNotFound", 404)
    reasoning = body.get("aiReasoning")
    if not isinstance(reasoning, str) or not trim(reasoning):
        raise ValidationError("errors.evaluationReasoningRequired")
    accuracy = body.get("accuracy")
    if accuracy not in ("correct", "wrong", "debatable"):
        raise ValidationError("errors.evaluationLabelInvalid")
    present = "humanVerdict" in body
    human = body.get("humanVerdict")
    if accuracy == "wrong":
        if human not in ("in_scope", "borderline", "out_of_scope"):
            raise ValidationError("errors.evaluationLabelInvalid")
    elif present:
        raise ValidationError("errors.evaluationLabelInvalid")
    return EvaluationLabel(
        UUID(history_id),
        EvaluationAccuracy(accuracy),
        trim(reasoning),
        Verdict(str(human)) if accuracy == "wrong" else None,
    )
