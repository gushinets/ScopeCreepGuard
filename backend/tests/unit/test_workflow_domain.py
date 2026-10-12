from copy import deepcopy

import pytest


def test_versioned_document_rejects_analysis_and_invalid_money():
    from scope_guard.domain.drafts.workflow import WorkflowError, empty_document, validate_document

    document = empty_document("en")
    assert validate_document(document)["reply"]["text"] == ""
    invalid = {**document, "result": {"verdict": "in_scope"}}
    with pytest.raises(WorkflowError):
        validate_document(invalid)
    invalid = deepcopy(document)
    invalid["reply"]["tone"] = "invented"
    with pytest.raises(WorkflowError):
        validate_document(invalid)


def test_hash_is_order_independent_but_preserves_request_text():
    from scope_guard.domain.drafts.workflow import operation_hash

    assert operation_hash({"a": 1, "b": 2}) == operation_hash({"b": 2, "a": 1})
    assert operation_hash({"request": " x"}) != operation_hash({"request": "x"})


def test_analysis_cannot_skip_running_or_change_terminal_state():
    from scope_guard.domain.drafts.workflow import WorkflowError, transition

    assert transition("analysis", "pending", "running") == "running"
    assert transition("analysis", "running", "succeeded") == "succeeded"
    with pytest.raises(WorkflowError):
        transition("analysis", "pending", "succeeded")
    with pytest.raises(WorkflowError):
        transition("analysis", "succeeded", "running")
    assert transition("export", "failed", "pending") == "pending"


def test_freshness_requires_exact_inputs_and_complete_provenance():
    from scope_guard.domain.drafts.workflow import analysis_matches

    run = {"status": "succeeded", "requestText": "request", "projectSnapshot": {"scope": "a"}}
    assert analysis_matches(run, "request", {"scope": "a"})
    assert not analysis_matches(run, "request", {"scope": "b"})
    assert not analysis_matches({**run, "projectSnapshot": None}, "request", {"scope": "a"})


def test_finalization_validates_exact_commercial_values():
    from scope_guard.domain.drafts.workflow import WorkflowError, validate_agreement

    agreement = {
        "description": "More work",
        "additionalCost": "2.675",
        "estimatedHours": "1",
        "currency": "USD",
        "noAdditionalCharge": False,
    }
    with pytest.raises(WorkflowError):
        validate_agreement(agreement)
    valid = validate_agreement({**agreement, "additionalCost": "2.67"})
    assert valid["additionalCost"] == "2.67"
    assert (
        validate_agreement({**agreement, "additionalCost": "", "noAdditionalCharge": True})[
            "additionalCost"
        ]
        == "0.00"
    )
