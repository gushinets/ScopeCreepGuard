"""Compatibility expectations derived from the existing TypeScript contracts."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURE = Path(__file__).parents[1] / "fixtures" / "contracts.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_project_input_normalizes_prices_and_ignores_browser_details():
    from scope_guard.modules.projects.schemas import CreateProjectRequest

    card = CreateProjectRequest.model_validate(fixture()["projectInput"])
    assert card.hourly_rate == "125.00"
    assert card.fixed_price is None
    assert card.client_name == "Acme"
    assert "endDate" not in card.model_dump(by_alias=True)


@pytest.mark.parametrize("amount", [True, "0", "-1", "1.234", "1e2", "1000000000000"])
def test_project_rejects_invalid_active_money(amount):
    from scope_guard.modules.projects.schemas import CreateProjectRequest

    with pytest.raises(ValidationError):
        CreateProjectRequest.model_validate({**fixture()["projectInput"], "hourlyRate": amount})


def test_full_card_update_preserves_client_omission_and_null():
    from scope_guard.modules.projects.schemas import UpdateProjectRequest

    card = fixture()["projectInput"]
    card.pop("clientName")
    omitted = UpdateProjectRequest.model_validate(card)
    assert "client_name" not in omitted.model_fields_set
    explicit = UpdateProjectRequest.model_validate({**card, "clientName": None})
    assert "client_name" in explicit.model_fields_set
    with pytest.raises(ValidationError):
        UpdateProjectRequest.model_validate({"name": "Rename only"})


def test_legacy_project_response_keeps_nulls_and_omits_last_checked():
    from scope_guard.modules.projects.schemas import ProjectResponse

    result = ProjectResponse.model_validate(fixture()["legacyProject"]).to_wire()
    assert result["hourlyRate"] is None
    assert result["startDate"] is None
    assert "lastChecked" not in result
    assert "userId" not in result


def test_saved_document_round_trip_keeps_editable_values_and_optional_snapshot_client():
    from scope_guard.modules.drafts.schemas import DraftDocument, ProjectSnapshot

    document = DraftDocument.model_validate(fixture()["document"])
    assert document.to_wire() == fixture()["document"]
    snapshot = ProjectSnapshot.model_validate(fixture()["snapshot"])
    assert "clientName" not in snapshot.to_wire()
    changed = copy.deepcopy(fixture()["document"])
    changed["changeOrder"]["additionalCost"] = ""
    changed["reply"]["text"] = ""
    assert DraftDocument.model_validate(changed).change_order.additional_cost == ""


@pytest.mark.parametrize("path,value", [("version", 2), ("reply.tone", "aggressive")])
def test_document_rejects_unsupported_version_or_tone(path, value):
    from scope_guard.modules.drafts.schemas import DraftDocument

    document = copy.deepcopy(fixture()["document"])
    target = document
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    with pytest.raises(ValidationError):
        DraftDocument.model_validate(document)


def test_document_size_counts_utf8_and_rejects_oversize_before_normalizing():
    from scope_guard.modules.drafts.schemas import DraftDocument

    document = copy.deepcopy(fixture()["document"])
    document["padding"] = "я" * 500_000
    with pytest.raises(ValidationError):
        DraftDocument.model_validate(document)


def test_label_requires_human_verdict_only_for_wrong():
    from scope_guard.modules.evaluations.schemas import EvaluationLabelRequest

    body = {
        "historyEntryId": "11111111-1111-4111-8111-111111111111",
        "accuracy": "correct",
        "aiReasoning": " reason ",
    }
    assert EvaluationLabelRequest.model_validate(body).ai_reasoning == "reason"
    with pytest.raises(ValidationError):
        EvaluationLabelRequest.model_validate({**body, "humanVerdict": None})
    with pytest.raises(ValidationError):
        EvaluationLabelRequest.model_validate({**body, "accuracy": "wrong"})


def test_contract_primitives_do_not_coerce_invalid_types():
    from scope_guard.modules.projects.schemas import CreateProjectRequest

    with pytest.raises(ValidationError):
        CreateProjectRequest.model_validate({**fixture()["projectInput"], "name": 123})
    with pytest.raises(ValidationError):
        CreateProjectRequest.model_validate(
            {**fixture()["projectInput"], "startDate": "2026-02-30"}
        )
