"""Controlled requests verify model inputs, not real-model compliance."""

import asyncio
import json
from copy import deepcopy

import pytest
from fixtures.llm_review import facts
from test_llm_review_corrections import RecordingStore, run

from scope_guard.domain.llm.commercial_terms import current_commercial_terms


@pytest.mark.parametrize("mode", ["saved", "rate", "free", "cleared", "missing", "preliminary"])
@pytest.mark.parametrize("tone", ["warm", "neutral", "firm"])
def test_provider_authority(mode, tone):
    source = facts(action="regenerate", tone=tone)
    source["analysis"].update(
        estimatedHours=3.5,
        additionalCost="105.00",
        reasoning="Historical proposal: 3.5 hours at 30 USD per hour.",
    )
    source["analysis"]["estimate"] = {
        "estimatedHours": 3.5,
        "additionalCost": "105.00",
        "currency": "USD",
    }
    source["document"]["reply"]["text"] = "Old proposal: 3.5 hours for 105 USD."
    saved = dict(
        estimatedHours="2.5",
        additionalCost="175.35",
        currency="USD",
        timelineImpact="Three working days after approval",
        endDate="",
        additionalTerms="Written approval required",
        noAdditionalCharge=mode == "free",
    )
    if mode == "cleared":
        saved.update(estimatedHours="", additionalCost="", currency="", timelineImpact="")
    if mode == "missing":
        saved = {}
    if mode != "preliminary":
        source["document"]["changeOrder"] = saved
    if mode == "rate":
        source["project"].update(hourlyRate="80.00", currency="EUR")
    source["currentCommercialTerms"] = deepcopy(current_commercial_terms(source))
    before = deepcopy(source)
    store = RecordingStore()
    asyncio.run(
        run(
            "reply",
            source,
            [{"scopePosition": "out_of_scope", "text": "Please approve these separate additions."}],
            store,
        )
    )
    request = store.calls[0]["request"]
    payload = json.loads(next(m["content"] for m in request.messages if m["role"] == "user"))
    assert set(payload) == {
        "locale",
        "request",
        "action",
        "selection",
        "scopeContext",
        "currentCommercialTerms",
        "previousReply",
    }
    assert payload["scopeContext"] == {
        "scope": before["project"]["scope"],
        "verdict": "out_of_scope",
        "citations": before["analysis"]["citations"],
        "hasAdditionalWork": True,
    }
    terms = payload["currentCommercialTerms"]
    assert terms == before["currentCommercialTerms"]
    assert terms["source"] == ("preliminaryEstimate" if mode == "preliminary" else "savedAgreement")
    assert terms["preliminary"] == (mode == "preliminary")
    if mode in ("saved", "rate", "free"):
        assert (terms["estimatedHours"], terms["additionalCost"], terms["currency"]) == (
            "2.5",
            "175.35",
            "USD",
        )
        assert terms["timelineImpact"] == saved["timelineImpact"]
        assert terms["additionalTerms"] == saved["additionalTerms"]
    elif mode == "cleared":
        assert terms["estimatedHours"] == terms["additionalCost"] == terms["currency"] == ""
    elif mode == "missing":
        assert terms["estimatedHours"] is terms["additionalCost"] is None
    else:
        assert terms["estimatedHours"] == 3.5 and terms["additionalCost"] == "105.00"
    assert terms["noAdditionalCharge"] == (mode == "free")
    prompt = " ".join(m["content"] for m in request.messages if m["role"] == "system")
    for rule in (
        "Rewrite only the selected reply",
        "override",
        "wording reference",
        "Do not recalculate price",
        "cleared conditions",
        "free work",
        "only when useful",
        "explicitly preliminary",
    ):
        assert rule in prompt
    assert source == before
    assert len(store.calls) == 1


@pytest.mark.parametrize("cleared", [False, True])
def test_local_diagnostics_use_current_terms_without_old_price_or_rate(cleared):
    from scope_guard.integrations.llm.stages import validate_text

    source = facts(action="regenerate")
    source["analysis"].update(estimatedHours=3.5, additionalCost="105.00")
    source["document"]["changeOrder"] = {
        "estimatedHours": "" if cleared else "2.5",
        "additionalCost": "" if cleared else "175.35",
        "currency": "" if cleared else "USD",
    }
    for obsolete in (
        "The additional work requires 3.5 hours for 105 USD.",
        "The additional work costs 30 USD per hour.",
    ):
        with pytest.raises(ValueError):
            validate_text("text", obsolete, "en", source)
    if not cleared:
        validate_text(
            "text", "The additional work requires 2.5 hours for 175.35 USD.", "en", source
        )


def test_frozen_terms_override_later_mutable_inputs():
    source = facts(action="regenerate")
    source["document"]["changeOrder"] = {"additionalCost": "175.35", "currency": "USD"}
    source["currentCommercialTerms"] = deepcopy(current_commercial_terms(source))
    source["document"]["changeOrder"]["additionalCost"] = "999.00"
    assert current_commercial_terms(source)["additionalCost"] == "175.35"


def test_semantic_review_uses_same_authoritative_projection():
    from fixtures.llm_ledger import APPROVED
    from test_any688_semantic_review import exercise

    from scope_guard.integrations.llm.prompts.workflow_v2 import stage_source

    source = facts(action="regenerate")
    source["document"]["changeOrder"] = {
        "estimatedHours": "2.5",
        "additionalCost": "175.35",
        "currency": "USD",
        "noAdditionalCharge": False,
        "timelineImpact": "Three working days after approval",
        "additionalTerms": "Written approval",
        "aiValues": {"additionalCost": "105.00"},
    }
    _, store, _, _ = asyncio.run(
        exercise(
            "Please confirm these additional terms before work starts.",
            "commercial_terms",
            decision=APPROVED,
            source=source,
        )
    )
    payload = json.loads(store.calls[1]["request"].messages[-1]["content"])
    assert payload["source"] == stage_source("reply", source)
    assert "savedDecisions" not in payload["source"]
    assert "aiValues" not in json.dumps(payload["source"])


def test_free_diagnostics_do_not_treat_saved_amount_as_payable():
    from scope_guard.integrations.llm.stages import validate_text

    source = facts(action="regenerate")
    source["document"]["changeOrder"] = {
        "estimatedHours": "2.5",
        "additionalCost": "175.35",
        "currency": "USD",
        "noAdditionalCharge": True,
    }
    with pytest.raises(ValueError):
        validate_text("text", "The additional work requires payment of 175.35 USD.", "en", source)
    validate_text(
        "text",
        (
            "These requested additions are outside the agreed scope and will be provided "
            "without additional payment. The additional fee is 0 USD. "
            "Please confirm the proposed conditions before we begin."
        ),
        "en",
        source,
    )
