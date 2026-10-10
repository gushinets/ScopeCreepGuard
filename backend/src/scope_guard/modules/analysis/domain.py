"""Detached, deeply immutable generation values. JSON is only frozen boundary data."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Absent:
    pass


ABSENT = Absent()


@dataclass(frozen=True, slots=True)
class FrozenObject:
    entries: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class FrozenArray:
    items: tuple[object, ...]


def freeze(value):
    if isinstance(value, dict):
        return FrozenObject(tuple((key, freeze(child)) for key, child in value.items()))
    if isinstance(value, list):
        return FrozenArray(tuple(freeze(child) for child in value))
    if value is None or isinstance(value, (str, bool, int, float, Absent)):
        return value
    raise ValueError("invalid_json_value")


def thaw(value):
    if isinstance(value, FrozenObject):
        return {key: thaw(child) for key, child in value.entries}
    if isinstance(value, FrozenArray):
        return [thaw(child) for child in value.items]
    return value


@dataclass(frozen=True, slots=True)
class LocaleResolution:
    value: str = "ru"
    failed: bool = False


@dataclass(frozen=True, slots=True)
class HistoricalSelector:
    draft_id: object = ABSENT
    proof: object = ABSENT
    locale: object = ABSENT


@dataclass(frozen=True, slots=True)
class AnalyzeCommand:
    project_id: str
    request: str
    end_date: str | None = None
    document_language: str | None = None


@dataclass(frozen=True, slots=True)
class RegenerateReplyCommand:
    project_id: str
    request: str
    tone: Literal["warm", "neutral", "firm"]
    previous_reply: str
    document_language: str | None = None


@dataclass(frozen=True, slots=True)
class MaterialsCommand:
    project_id: str
    request: str
    client_language: str
    analysis: object
    input_length: int
    selector: HistoricalSelector
    history_id: str | Absent = ABSENT


@dataclass(frozen=True, slots=True)
class EstimateCommand:
    project_id: str
    request: str
    selector: HistoricalSelector
    end_date: str | None = None
    document_language: str | None = None


@dataclass(frozen=True, slots=True)
class Replies:
    warm: str
    neutral: str
    firm: str


@dataclass(frozen=True, slots=True)
class Labels:
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ChangeOrder:
    description: str
    timeline_impact: str
    additional_cost: str
    note: str
    estimated_hours: float | Absent = ABSENT
    currency: str | Absent = ABSENT
    rationale: str | Absent = ABSENT


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    verdict: str
    confidence: int
    summary: str
    reasoning: str
    citations: tuple[str, ...]
    replies: Replies
    change_order: ChangeOrder
    client_language: str
    change_order_labels: Labels | Absent = ABSENT
    has_additional_work: bool | Absent = ABSENT
    request_language: str | Absent = ABSENT
    estimate_valid: bool | Absent = ABSENT
    suggestion: str | Absent = ABSENT
    draft_created_at: str | Absent = ABSENT
    commercial_signature: str | Absent = ABSENT


@dataclass(frozen=True, slots=True)
class ClientChangeOrder:
    description: str
    timeline_impact: str
    rationale: str
    note: str


@dataclass(frozen=True, slots=True)
class ClientMaterials:
    client_language: str
    replies: Replies
    change_order: ClientChangeOrder | None
    change_order_labels: Labels | Absent = ABSENT


@dataclass(frozen=True, slots=True)
class GenerationContext:
    project_id: str
    name: str
    client_name: str | None | Absent
    industry: str
    scope: str
    start_date: str | None
    pricing_model: str | None
    currency: str | None
    hourly_rate: str | None
    fixed_price: str | None


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    context: GenerationContext
    request: str
    locale: str
    end_date: str | None = None
    draft_created_at: str | None = None
    document_language: str | None = None


@dataclass(frozen=True, slots=True)
class ReplyInput:
    context: GenerationContext
    request: str
    locale: str
    tone: str
    previous_reply: str
    document_language: str | None = None


@dataclass(frozen=True, slots=True)
class MaterialInput:
    context: GenerationContext
    request: str
    locale: str
    client_language: str
    analysis: AnalysisResult


@dataclass(frozen=True, slots=True)
class ProjectSnapshotV1:
    context: GenerationContext
    end_date: str | None
    document_language: str | None


@dataclass(frozen=True, slots=True)
class DraftProofBinding:
    user_id: str
    project_id: str
    request: str
    locale: str


@dataclass(frozen=True, slots=True)
class DraftProofClaims:
    binding: DraftProofBinding
    analysis_snapshot: AnalysisResult
    project_snapshot: FrozenObject


@dataclass(frozen=True, slots=True)
class AnalyzeOutcome:
    result: AnalysisResult
    project_snapshot: ProjectSnapshotV1
    proof: str


@dataclass(frozen=True, slots=True)
class ReplyOutcome:
    reply: str


@dataclass(frozen=True, slots=True)
class MaterialsOutcome:
    materials: ClientMaterials


@dataclass(frozen=True, slots=True)
class EstimateOutcome:
    result: AnalysisResult


class GenerationError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = "errors." + code, status
        super().__init__(self.code)
