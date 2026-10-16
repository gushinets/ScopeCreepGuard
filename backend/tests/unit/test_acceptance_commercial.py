from copy import deepcopy

import pytest

from scope_guard.domain.change_orders.merge import merge_estimate


@pytest.mark.parametrize(
    "manual",
    [
        {"additionalCost": "175.35"},
        {"currency": "EUR"},
        {"additionalCost": "175.35", "currency": "RUB"},
        {"estimatedHours": "2.5", "additionalCost": "175.35"},
        {"noAdditionalCharge": True},
    ],
)
def test_manual_commercial_value_is_atomic_and_rationale_is_not_misattributed(manual):
    ai = {
        "estimatedHours": "8.00",
        "additionalCost": "240.00",
        "currency": "USD",
        "rationale": "8 hours at 30 USD/hour",
    }
    saved = {**ai, "aiValues": deepcopy(ai), "noAdditionalCharge": False, **manual}
    original = deepcopy(saved)
    suggestion = {
        "estimatedHours": "8.00",
        "additionalCost": "640.00",
        "currency": "EUR",
        "rationale": "8 hours at 80 EUR/hour",
    }
    result = merge_estimate(saved, suggestion)
    assert saved == original
    if "additionalCost" in manual or "currency" in manual or manual.get("noAdditionalCharge"):
        assert (result["additionalCost"], result["currency"]) == (
            saved["additionalCost"],
            saved["currency"],
        )
    assert all(result["aiValues"][field] == value for field, value in suggestion.items())
    assert result["rationale"] == ""
    assert result["noAdditionalCharge"] == saved["noAdditionalCharge"]
    if "estimatedHours" in manual:
        assert result["estimatedHours"] == manual["estimatedHours"]
    again = merge_estimate(result, suggestion)
    assert again == result


def test_untouched_ai_terms_refresh_together_and_manual_rationale_survives():
    ai = {
        "estimatedHours": "8",
        "additionalCost": "240.00",
        "currency": "USD",
        "rationale": "Original estimate",
    }
    saved = {**ai, "estimatedHours": "8.00", "aiValues": ai, "noAdditionalCharge": False}
    suggestion = {
        "estimatedHours": "4",
        "additionalCost": "320.00",
        "currency": "EUR",
        "rationale": "Updated estimate",
    }
    assert merge_estimate(saved, suggestion) == {**saved, **suggestion, "aiValues": suggestion}
    saved.update(additionalCost="175.35", rationale="My agreed package price")
    assert merge_estimate(saved, suggestion)["rationale"] == "My agreed package price"


def test_manual_ownership_survives_matching_suggestion_reload_and_later_refresh():
    ai = {
        "estimatedHours": "8",
        "additionalCost": "240.00",
        "currency": "USD",
        "rationale": "Original estimate",
    }
    saved = {**ai, "estimatedHours": "2.5", "additionalCost": "175.35", "aiValues": ai}
    matching = {
        "estimatedHours": "2.5",
        "additionalCost": "175.35",
        "currency": "USD",
        "rationale": "Matching suggestion",
    }
    first = merge_estimate(saved, matching)
    restored = deepcopy(first)
    changed = {
        "estimatedHours": "10",
        "additionalCost": "800",
        "currency": "EUR",
        "rationale": "Different suggestion",
    }
    final = merge_estimate(restored, changed)
    assert (final["estimatedHours"], final["additionalCost"], final["currency"]) == (
        "2.5",
        "175.35",
        "USD",
    )
    assert final["aiValues"]["additionalCost"] == "800"
