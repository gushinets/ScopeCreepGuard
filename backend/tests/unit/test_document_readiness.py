import pytest

from scope_guard.domain.change_orders.readiness import document_readiness
from scope_guard.domain.drafts.workflow import WorkflowError, validate_agreement

VALID = {
    "providerName": "Studio",
    "clientName": "Clinic",
    "description": "Add email alerts",
    "estimatedHours": "2.5",
    "additionalCost": "175.35",
    "currency": "USD",
    "timelineImpact": "3 working days after approval",
    "noAdditionalCharge": False,
}


@pytest.mark.parametrize(
    "field",
    [
        "providerName",
        "clientName",
        "description",
        "estimatedHours",
        "additionalCost",
        "currency",
        "timelineImpact",
    ],
)
def test_readiness_identifies_individual_omissions_without_mutating_draft(field):
    draft = {**VALID, field: ""}
    assert document_readiness(draft) == {field: "required"}
    assert draft[field] == ""


def test_combined_and_optional_free_work_cases():
    assert set(document_readiness({})) == {
        "providerName",
        "clientName",
        "description",
        "estimatedHours",
        "additionalCost",
        "currency",
        "timelineImpact",
    }
    assert document_readiness({**VALID, "clientEmail": "", "approvalDate": ""}) == {}
    free = {**VALID, "additionalCost": "", "currency": "", "noAdditionalCharge": True}
    assert document_readiness(free) == {}
    assert validate_agreement(free)["additionalCost"] == "0.00"


def test_finalize_returns_existing_blocking_requirements_as_fields():
    with pytest.raises(WorkflowError) as error:
        validate_agreement({**VALID, "description": "", "additionalCost": "", "currency": ""})
    assert error.value.fields == {
        "description": "required",
        "additionalCost": "required",
        "currency": "required",
    }
    # Parties and a schedule remain readiness warnings, not new mandatory API fields.
    assert validate_agreement({**VALID, "providerName": "", "clientName": "", "timelineImpact": ""})
