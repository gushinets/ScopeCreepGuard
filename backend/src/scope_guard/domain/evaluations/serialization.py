from scope_guard.domain.evaluations.domain import EvaluationExport
from scope_guard.domain.shared.js_compat import stringify

VERDICTS = {
    "in_scope": "IN_SCOPE",
    "borderline": "BORDERLINE",
    "out_of_scope": "OUT_OF_SCOPE",
}


def serialize_jsonl(rows: tuple[EvaluationExport, ...]) -> bytes:
    if not rows:
        return b""
    records = []
    for row in rows:
        records.append(
            stringify(
                {
                    "scope": row.scope,
                    "request": row.request,
                    "ai_verdict": VERDICTS[row.ai_verdict.value],
                    "human_verdict": (
                        VERDICTS[row.human_verdict.value] if row.human_verdict is not None else None
                    ),
                    "ai_reasoning": row.ai_reasoning,
                    "project_type": row.industry.value.lower(),
                }
            )
        )
    return ("\n".join(records) + "\n").encode("utf-8")
