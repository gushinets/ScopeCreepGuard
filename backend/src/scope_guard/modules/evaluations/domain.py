from scope_guard.core.contracts import EvaluationAccuracy, Verdict
from scope_guard.modules.evaluations.schemas import EvaluationLabelRequest


def resolve_human_verdict(label: EvaluationLabelRequest, ai_verdict: Verdict) -> Verdict | None:
    if label.accuracy == EvaluationAccuracy.debatable:
        return None
    if label.accuracy == EvaluationAccuracy.correct:
        return ai_verdict
    if label.human_verdict == ai_verdict:
        raise ValueError("evaluation_label_invalid")
    return label.human_verdict
