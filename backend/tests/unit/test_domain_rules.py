import copy
from decimal import Decimal

import pytest
from test_contracts import fixture


def test_commercial_terms_uses_decimal_and_does_not_mirror_legacy_rows():
    from scope_guard.modules.projects.domain import CommercialTerms
    from scope_guard.modules.projects.schemas import CreateProjectRequest

    terms = CommercialTerms.from_project_input(
        CreateProjectRequest.model_validate(fixture()["projectInput"])
    )
    assert terms.amount == Decimal("125.00")


def test_edits_allow_document_money_but_protect_original_analysis():
    from scope_guard.modules.analysis.schemas import AnalysisSnapshot
    from scope_guard.modules.drafts.domain import validate_document_against_snapshot
    from scope_guard.modules.drafts.schemas import DraftDocument

    document = copy.deepcopy(fixture()["document"])
    document["changeOrder"]["additionalCost"] = "99"
    snapshot = AnalysisSnapshot.model_validate(fixture()["analysis"])
    validate_document_against_snapshot(DraftDocument.model_validate(document), snapshot)
    document["result"]["citations"] = ["Forged"]
    with pytest.raises(ValueError, match="immutable_analysis"):
        validate_document_against_snapshot(DraftDocument.model_validate(document), snapshot)


def test_evaluation_resolution_rejects_wrong_equal_to_ai():
    from scope_guard.core.contracts import Verdict
    from scope_guard.modules.evaluations.domain import resolve_human_verdict
    from scope_guard.modules.evaluations.schemas import EvaluationLabelRequest

    base = {"historyEntryId": "11111111-1111-4111-8111-111111111111", "aiReasoning": "reason"}
    assert (
        resolve_human_verdict(
            EvaluationLabelRequest.model_validate({**base, "accuracy": "debatable"}),
            Verdict.in_scope,
        )
        is None
    )
    assert (
        resolve_human_verdict(
            EvaluationLabelRequest.model_validate({**base, "accuracy": "correct"}), Verdict.in_scope
        )
        == Verdict.in_scope
    )
    with pytest.raises(ValueError, match="evaluation_label_invalid"):
        resolve_human_verdict(
            EvaluationLabelRequest.model_validate(
                {**base, "accuracy": "wrong", "humanVerdict": "in_scope"}
            ),
            Verdict.in_scope,
        )
