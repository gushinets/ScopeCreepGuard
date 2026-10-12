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


def validate_document_against_snapshot(document: dict, snapshot: dict) -> None:
    candidate, original = document["result"], snapshot
    missing = object()
    if any(
        candidate.get(field, missing) != original.get(field, missing) for field in PROTECTED_FIELDS
    ):
        raise ValueError("immutable_analysis")
