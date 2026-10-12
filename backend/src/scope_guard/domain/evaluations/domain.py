from dataclasses import dataclass
from uuid import UUID

from scope_guard.domain.shared.enums import EvaluationAccuracy, Industry, Verdict


@dataclass(frozen=True, slots=True)
class EvaluationLabel:
    history_entry_id: UUID
    accuracy: EvaluationAccuracy
    ai_reasoning: str
    human_verdict: Verdict | None = None


@dataclass(frozen=True, slots=True)
class EvaluationExport:
    scope: str
    request: str
    ai_verdict: Verdict
    human_verdict: Verdict | None
    ai_reasoning: str
    industry: Industry


@dataclass(frozen=True, slots=True)
class OwnedHistoryContext:
    id: UUID
    scope: str
    request: str
    ai_verdict: Verdict
    industry: Industry


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    id: UUID
    accuracy: EvaluationAccuracy
    human_verdict: Verdict | None
