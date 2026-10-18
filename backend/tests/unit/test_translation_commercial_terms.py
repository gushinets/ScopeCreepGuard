"""Commercial translation failures through the native runner and accounted gateway."""

import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest
from fixtures.llm_review import facts, order
from test_llm_review_corrections import RecordingStore, run

from scope_guard.domain.llm.runtime import Binding, GatewayFailure, ProviderResponse
from scope_guard.integrations.llm.diagnostics import local_observations
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner

ACCEPT = {"decision": "accept", "violations": []}


def rejection(stage):
    return {
        "decision": "reject",
        "violations": [
            {
                "field": "warm" if stage == "replies" else "rationale",
                "rule": "commercial_terms",
                "feedback": "Preserve the saved fee and currency.",
            }
        ],
    }


def generations(store):
    return [c for c in store.calls if not c["request"].schema_name.startswith("semantic_review_")]


def saved_source(amount="220", currency="EUR", *, free=False):
    source = facts("es", "translate")
    source["document"]["reply"].update(
        language="en",
        text="These additions cost 240 USD.",
        generated=dict.fromkeys(("warm", "neutral", "firm"), "These additions cost 240 USD."),
    )
    source["document"]["changeOrder"] = {
        **order("en"),
        "additionalCost": amount,
        "currency": currency,
        "estimatedHours": "8",
        "noAdditionalCharge": free,
        "aiValues": {"additionalCost": "240", "currency": "USD", "estimatedHours": "8"},
        "rationale": "These additions cost 240 USD.",
    }
    source["project"].update(hourlyRate="80", currency="RUB")
    return source


def candidate(stage, text):
    value = order("es") if stage == "change_order" else {"scopePosition": "out_of_scope"}
    if stage == "change_order":
        value["rationale"] = text
    else:
        value.update(dict.fromkeys(("warm", "neutral", "firm"), text))
    return value


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize("bad", ["240 euros", "220 USD", "240 USD", "22 EUR"])
def test_wrong_commercial_prose_corrects_with_current_saved_pair(stage, bad):
    store, source = RecordingStore(), saved_source()
    before = deepcopy(source)
    value = asyncio.run(
        run(
            stage,
            source,
            [
                candidate(stage, f"Estos cambios cuestan {bad}."),
                candidate(stage, "Estos cambios cuestan 220 EUR."),
            ],
            store,
            reviews=[rejection(stage), ACCEPT],
        )
    )
    assert value["warm" if stage == "replies" else "rationale"].endswith("220 EUR.")
    assert len(store.calls) == 4
    assert store.calls[0]["rejected"]
    feedback = str(store.feedbacks)
    assert "220 EUR" in feedback and "commercial_terms" in feedback
    assert all(c["response"].input_tokens == 100 for c in store.calls)
    request = store.calls[0]["request"]
    payload = json.loads(next(m["content"] for m in request.messages if m["role"] == "user"))
    assert payload["currentCommercialTerms"]["additionalCost"] == "220"
    assert payload["currentCommercialTerms"]["currency"] == "EUR"
    assert "hourlyRate" not in payload["project"] and "currency" not in payload["project"]
    assert "additionalCost" not in payload["analysis"]
    review_payload = json.loads(store.calls[1]["request"].messages[-1]["content"])
    assert review_payload["source"]["currentCommercialTerms"]["additionalCost"] == "220"
    assert "savedDecisions" not in review_payload["source"]
    assert "aiValues" not in json.dumps(review_payload["source"])
    assert "hourlyRate" not in json.dumps(review_payload["source"])
    assert source == before


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize(
    "amount,currency,text",
    [
        ("240", "USD", "Estos cambios cuestan 240 USD."),
        ("220", "EUR", "Estos cambios cuestan 220 EUR."),
        ("175.35", "USD", "Estos cambios cuestan 175,35 USD."),
    ],
)
def test_saved_pair_and_localized_decimal_are_accepted_once(stage, amount, currency, text):
    store = RecordingStore()
    value = asyncio.run(run(stage, saved_source(amount, currency), [candidate(stage, text)], store))
    assert value["warm" if stage == "replies" else "rationale"] == text
    assert len(generations(store)) == 1 and not store.feedbacks
    assert len(store.calls) == 2


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize("mode", ["free", "cleared", "missing"])
def test_free_or_empty_saved_terms_cannot_revive_historical_price(stage, mode):
    source, store = saved_source(free=mode == "free"), RecordingStore()
    if mode != "free":
        source["document"]["changeOrder"].update(additionalCost="", currency="")
    if mode == "missing":
        source["document"]["changeOrder"].pop("additionalCost")
    good = "Estos cambios se realizarán sin coste adicional."
    value = asyncio.run(
        run(
            stage,
            source,
            [
                candidate(stage, "Estos cambios cuestan 240 USD."),
                candidate(stage, good),
            ],
            store,
        )
    )
    assert value["warm" if stage == "replies" else "rationale"] == good
    assert len(store.calls) == 3 and store.calls[0]["rejected"]


def test_commercial_correction_exhausts_at_three_calls():
    store = RecordingStore()
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(
            run(
                "replies",
                saved_source(),
                [
                    candidate("replies", "Estos cambios cuestan 240 euros."),
                ],
                store,
                reviews=[rejection("replies")],
            )
        )
    assert [c["request"].semantic_attempt for c in generations(store)] == [1, 2, 3]
    assert len(store.calls) == 6


def test_recovered_candidate_is_checked_before_reuse_without_resetting_attempt_budget():
    class RecoveredStore(RecordingStore):
        async def feedback(self, binding, error):
            self.feedbacks.append(error)

    source, store = saved_source("240", "USD"), RecoveredStore()
    binding = Binding(uuid4(), uuid4(), 1, "controlled", "medium", semantic_start=3)
    runner = StructuredStageRunner(ProviderGateway(store, None), store)
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(
            runner.run(
                binding,
                "replies",
                source,
                {
                    "candidate": json.dumps(
                        candidate("replies", "Estos cambios cuestan 240 euros.")
                    ),
                },
            )
        )
    assert not store.calls


@pytest.mark.parametrize("stage", ["replies", "change_order"])
def test_omitting_saved_fee_does_not_evade_the_commercial_guard(stage):
    store = RecordingStore()
    value = asyncio.run(
        run(
            stage,
            saved_source(),
            [
                candidate(stage, "Estos cambios requieren su aprobación."),
                candidate(stage, "Estos cambios cuestan 220 EUR."),
            ],
            store,
            reviews=[rejection(stage), ACCEPT],
        )
    )
    assert value["warm" if stage == "replies" else "rationale"].endswith("220 EUR.")
    assert len(store.calls) == 4


def test_diagnostics_do_not_restore_an_old_fee_after_conversion():
    source = saved_source()
    observed = local_observations(
        Binding(uuid4(), uuid4(), 1, "controlled", "medium"),
        "replies",
        candidate("replies", "Estos cambios cuestan 220 EUR."),
        source,
    )
    assert not any(o.rule == "commercial_terms" and o.outcome == "finding" for o in observed)


@pytest.mark.parametrize("field", ["additionalTerms", "rationale"])
def test_installments_are_preserved_instead_of_rewritten_to_the_total_fee(field):
    source, store = saved_source("240", "USD"), RecordingStore()
    source["analysis"].update(additionalCost="120", currency="USD")
    source["document"]["changeOrder"][field] = "120 USD deposit and remaining 120 USD on delivery."
    before = deepcopy(source)
    translated = candidate("change_order", "Estos cambios cuestan 240 USD.")
    translated[field] = "240 USD de anticipo y 240 USD al finalizar."
    corrected = deepcopy(translated)
    corrected[field] = "120 USD de anticipo y 120 USD al finalizar."
    reject = {
        "decision": "reject",
        "violations": [
            {
                "field": field,
                "rule": "commercial_terms",
                "feedback": "Preserve both installments.",
            }
        ],
    }
    value = asyncio.run(
        run("change_order", source, [translated, corrected], store, reviews=[reject, ACCEPT])
    )
    assert value[field] == "120 USD de anticipo y 120 USD al finalizar."
    assert source == before
    assert len(store.calls) == 4 and generations(store)[0]["rejected"]


def test_recovered_contextual_acceptance_is_reused_without_provider_calls():
    source, store = saved_source(), RecordingStore()
    translated = candidate("replies", "Estos cambios cuestan 220 EUR.")
    binding = Binding(uuid4(), uuid4(), 1, "controlled", "medium")
    for attempt in range(1, 4):
        store.review_slot(binding, "replies", attempt)

    class Adapter:
        async def request(self, request, timeout):
            value = ACCEPT if request.schema_name == "semantic_review_v2" else translated
            return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=50)

    async def exercise():
        runner = StructuredStageRunner(ProviderGateway(store, Adapter()), store)
        value = await runner.run(binding, "replies", source, {})
        assert value == translated and len(store.calls) == 2
        # Crash after review acceptance but before stage acceptance/publication.
        value = await StructuredStageRunner(ProviderGateway(store, None), store).run(
            replace(binding, semantic_start=1),
            "replies",
            source,
            {"candidate": json.dumps(translated)},
        )
        assert value == translated and len(store.calls) == 2

    asyncio.run(exercise())


def test_contextual_check_covers_monetary_claims_without_recognized_amounts():
    source, store = saved_source("240", "USD"), RecordingStore()
    source["document"]["reply"].update(
        text="The additional fee requires separate approval.",
        generated=dict.fromkeys(
            ("warm", "neutral", "firm"), "The additional fee requires separate approval."
        ),
    )
    value = asyncio.run(
        run(
            "replies",
            source,
            [
                candidate("replies", "El importe de la remuneración se duplica."),
                candidate("replies", "El importe adicional requiere su aprobación."),
            ],
            store,
            reviews=[rejection("replies"), ACCEPT],
        )
    )
    assert value["warm"] == "El importe adicional requiere su aprobación."
    assert len(store.calls) == 4 and generations(store)[0]["rejected"]
