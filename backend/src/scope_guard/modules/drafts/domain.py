from scope_guard.modules.analysis.schemas import AnalysisSnapshot
from scope_guard.modules.drafts.schemas import DraftDocument

PROTECTED_FIELDS = (
    "verdict",
    "confidence",
    "summary",
    "reasoning",
    "citations",
    "suggestion",
    "hasAdditionalWork",
    "requestLanguage",
)


def validate_document_against_snapshot(document: DraftDocument, snapshot: AnalysisSnapshot) -> None:
    candidate, original = document.result.to_wire(), snapshot.to_wire()
    missing = object()
    if any(
        candidate.get(field, missing) != original.get(field, missing) for field in PROTECTED_FIELDS
    ):
        raise ValueError("immutable_analysis")
