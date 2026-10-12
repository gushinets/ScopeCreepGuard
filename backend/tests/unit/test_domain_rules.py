import copy
from decimal import Decimal

import pytest
from test_contracts import fixture


def test_commercial_terms_uses_decimal_and_does_not_mirror_legacy_rows():
    from scope_guard.domain.projects.domain import CommercialTerms
    from scope_guard.modules.projects.schemas import CreateProjectRequest

    terms = CommercialTerms.from_project_input(
        CreateProjectRequest.model_validate(fixture()["projectInput"])
    )
    assert terms.amount == Decimal("125.00")


def test_edits_allow_document_money_but_protect_original_analysis():
    from scope_guard.modules.analysis.schemas import AnalysisSnapshot
    from scope_guard.domain.drafts.domain import validate_document_against_snapshot
    from scope_guard.modules.drafts.schemas import DraftDocument

    document = copy.deepcopy(fixture()["document"])
    document["changeOrder"]["additionalCost"] = "99"
    snapshot = AnalysisSnapshot.model_validate(fixture()["analysis"])
    validate_document_against_snapshot(
        DraftDocument.model_validate(document).to_wire(), snapshot.to_wire()
    )
    document["result"]["citations"] = ["Forged"]
    with pytest.raises(ValueError, match="immutable_analysis"):
        validate_document_against_snapshot(
            DraftDocument.model_validate(document).to_wire(), snapshot.to_wire()
        )


def test_evaluation_resolution_rejects_wrong_equal_to_ai():
    from scope_guard.core.contracts import Verdict
    from scope_guard.domain.evaluations.domain import EvaluationLabel
    from scope_guard.modules.evaluations.schemas import EvaluationLabelRequest
    from scope_guard.services.evaluations.use_cases import EvaluationError, resolve_human_verdict

    def parsed(value):
        return EvaluationLabel(**EvaluationLabelRequest.model_validate(value).model_dump())

    base = {"historyEntryId": "11111111-1111-4111-8111-111111111111", "aiReasoning": "reason"}
    assert (
        resolve_human_verdict(
            parsed({**base, "accuracy": "debatable"}),
            Verdict.in_scope,
        )
        is None
    )
    assert (
        resolve_human_verdict(parsed({**base, "accuracy": "correct"}), Verdict.in_scope)
        == Verdict.in_scope
    )
    with pytest.raises(EvaluationError, match="evaluationLabelInvalid"):
        resolve_human_verdict(
            parsed({**base, "accuracy": "wrong", "humanVerdict": "in_scope"}),
            Verdict.in_scope,
        )
