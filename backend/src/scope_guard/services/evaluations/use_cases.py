from collections.abc import Callable
from uuid import UUID

from scope_guard.domain.evaluations.domain import (
    EvaluationExport,
    EvaluationLabel,
    EvaluationResult,
)
from scope_guard.domain.evaluations.repository import EvaluationWork
from scope_guard.domain.shared.enums import Verdict
from scope_guard.services.evaluations.queries import EvaluationReadWork


class EvaluationError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = "errors." + code, status
        super().__init__(self.code)


def resolve_human_verdict(label: EvaluationLabel, ai_verdict: Verdict) -> Verdict | None:
    if label.accuracy.value == "debatable":
        return None
    if label.accuracy.value == "correct":
        return ai_verdict
    if label.human_verdict == ai_verdict:
        raise EvaluationError("evaluationLabelInvalid")
    return label.human_verdict


class EvaluationService:
    def __init__(
        self,
        factory: Callable[[], EvaluationWork],
        reads: Callable[[], EvaluationReadWork] | None = None,
    ):
        self.factory = factory
        self.reads = reads or factory

    async def label(self, owner: str, value: EvaluationLabel) -> EvaluationResult:
        async with self.factory() as work:
            context = await work.evaluations.history_owned(UUID(owner), value.history_entry_id)
            if context is None:
                raise EvaluationError("evaluationHistoryNotFound", 404)
            result = await work.evaluations.upsert(
                UUID(owner), context, value, resolve_human_verdict(value, context.ai_verdict)
            )
            await work.commit()
            return result

    async def export(self, owner: str) -> tuple[EvaluationExport, ...]:
        async with self.reads() as work:
            return await work.evaluations.list_owned(UUID(owner))
