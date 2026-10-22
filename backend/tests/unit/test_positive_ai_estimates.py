import pytest

from scope_guard.integrations.llm.stages import validate_stage


@pytest.mark.parametrize("stage", ["analysis", "estimate"])
@pytest.mark.parametrize("pricing", ["hourly", "fixed"])
@pytest.mark.parametrize("hours,cost", [(0, "0.00"), (0, "240"), (8, "0")])
def test_zero_ai_proposal_for_additional_work_is_rejected(stage, pricing, hours, cost):
    facts = {
        "locale": "en",
        "selection": {"selectedLanguage": "en"},
        "project": {
            "scope": "Five pages",
            "pricingModel": pricing,
            "currency": "USD",
            "hourlyRate": "30",
            "fixedPrice": "1000",
        },
        "analysis": {"verdict": "out_of_scope", "hasAdditionalWork": True},
    }
    value = {"hasAdditionalWork": True, "estimatedHours": hours, "additionalCost": cost}
    with pytest.raises(ValueError, match="estimate.positive"):
        validate_stage(stage, value, facts)


@pytest.mark.parametrize("additional", [True, False])
def test_included_work_and_positive_estimates_remain_valid(additional):
    facts = {
        "locale": "en",
        "selection": {"selectedLanguage": "en"},
        "project": {
            "scope": "Five pages",
            "pricingModel": "hourly",
            "currency": "USD",
            "hourlyRate": "30",
        },
    }
    value = {
        "verdict": "out_of_scope" if additional else "in_scope",
        "hasAdditionalWork": additional,
        "estimatedHours": 8 if additional else 0,
        "additionalCost": "240.00" if additional else "0",
        "currency": "USD",
        "summary": "",
        "reasoning": "",
        "suggestion": "",
        "citations": [],
    }
    assert validate_stage("analysis", value, facts) == value
