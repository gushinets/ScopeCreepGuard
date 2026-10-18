"""Structured preservation is blocking; monetary prose correctness is diagnostic only."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fixtures.llm_review import facts, order
from test_llm_review_corrections import RecordingStore, run

from scope_guard.domain.llm.runtime import Binding, GatewayFailure, ProviderResponse, digest
from scope_guard.integrations.llm.diagnostics import local_observations
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker


def source(amount="220", currency="EUR", free=False):
    value = facts("es", "translate")
    value["document"]["reply"]["language"] = "en"
    value["document"]["changeOrder"] = {
        **order("en"),
        "additionalCost": amount,
        "currency": currency,
        "estimatedHours": "8",
        "noAdditionalCharge": free,
    }
    value["project"].update(hourlyRate="80", currency="RUB")
    return value


def output(
    stage, amount="220", currency="EUR", free=False, text="Estos cambios cuestan 240 euros."
):
    value = (
        order("es")
        if stage == "change_order"
        else {
            "scopePosition": "out_of_scope",
            **dict.fromkeys(("warm", "neutral", "firm"), text),
        }
    )
    if stage == "change_order":
        value["rationale"] = text
    value["commercialTerms"] = {"amount": amount, "currency": currency, "noAdditionalCharge": free}
    return value


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize(
    "bad",
    [
        {"amount": "240", "currency": "EUR", "noAdditionalCharge": False},
        {"amount": "220", "currency": "USD", "noAdditionalCharge": False},
        {"amount": "220", "currency": "EUR", "noAdditionalCharge": True},
    ],
)
def test_wrong_structured_terms_correct_only_the_stage(stage, bad):
    store, frozen = RecordingStore(), source()
    before = deepcopy(frozen)
    wrong, good = output(stage), output(stage)
    wrong["commercialTerms"] = bad
    value = asyncio.run(run(stage, frozen, [wrong, good], store))
    assert "commercialTerms" not in value
    assert len(store.calls) == 2 and store.calls[0]["rejected"]
    assert all(c["request"].schema_name == stage + "_v1" for c in store.calls)
    assert "commercialTerms." in str(store.feedbacks) and "220 EUR" in str(store.feedbacks)
    assert frozen == before
    payload = json.loads(
        next(m["content"] for m in store.calls[0]["request"].messages if m["role"] == "user")
    )
    assert payload["commercialTerms"] == {
        "amount": "220",
        "currency": "EUR",
        "noAdditionalCharge": False,
    }
    assert payload["currentCommercialTerms"]["additionalCost"] == "220"
    assert "hourlyRate" not in payload["project"] and "currency" not in payload["project"]
    assert "additionalCost" not in payload["analysis"]


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize(
    "saved,returned,currency",
    [
        ("240", "240.00", "USD"),
        ("220", "220.000", "EUR"),
        ("175.35", "175.350", "USD"),
        ("0", "0.00", "USD"),
    ],
)
def test_decimal_equivalence_and_saved_pair_need_one_call(stage, saved, returned, currency):
    store = RecordingStore()
    value = asyncio.run(
        run(stage, source(saved, currency), [output(stage, returned, currency)], store)
    )
    assert "commercialTerms" not in value
    assert len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize("stage", ["replies", "change_order"])
@pytest.mark.parametrize(
    "amount,currency,free",
    [("", "", False), (None, None, False), ("175.35", "USD", True), ("", "USD", False)],
)
def test_empty_and_free_are_not_zero_or_historical_estimates(stage, amount, currency, free):
    store = RecordingStore()
    returned = output(
        stage,
        None if amount in (None, "") else amount,
        None if currency in (None, "") else currency,
        free,
    )
    asyncio.run(run(stage, source(amount, currency, free), [returned], store))
    assert len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize("stage", ["replies", "change_order"])
def test_wrong_structured_terms_exhaust_at_three_accounted_calls(stage):
    store = RecordingStore()
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(run(stage, source(), [output(stage, "240", "USD")], store))
    assert [c["request"].semantic_attempt for c in store.calls] == [1, 2, 3]
    assert all(c.get("rejected") and c["response"].input_tokens == 100 for c in store.calls)


@pytest.mark.parametrize(
    "text",
    [
        "Estos cambios cuestan 240 euros.",
        "220 EUR, 220 EUR, 220 EUR.",
        "Estos cambios requieren su aprobación.",
    ],
)
@pytest.mark.parametrize("stage", ["replies", "change_order"])
def test_intentional_limitation_wrong_repeated_or_omitted_prose_does_not_block(stage, text):
    store = RecordingStore()
    value = asyncio.run(run(stage, source(), [output(stage, text=text)], store))
    assert value["warm" if stage == "replies" else "rationale"] == text
    assert len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"amount": 220, "currency": "EUR", "noAdditionalCharge": False},
        {"amount": "220", "currency": "EUR", "noAdditionalCharge": "false"},
        {"amount": "220", "currency": "EUR"},
    ],
)
def test_native_commercial_object_is_required_and_strict(bad):
    store = RecordingStore()
    wrong = output("replies")
    wrong["commercialTerms"] = bad
    asyncio.run(run("replies", source(), [wrong, output("replies")], store))
    assert len(store.calls) == 2 and store.calls[0]["rejected"]


@pytest.mark.parametrize(
    "saved_amount,saved_currency,free", [("", "", False), ("175.35", "USD", True)]
)
def test_zero_does_not_replace_empty_or_free_saved_metadata(saved_amount, saved_currency, free):
    store = RecordingStore()
    frozen = source(saved_amount, saved_currency, free)
    good = output("replies", saved_amount or None, saved_currency or None, free)
    asyncio.run(run("replies", frozen, [output("replies", "0", "USD"), good], store))
    assert len(store.calls) == 2 and store.calls[0]["rejected"]


def test_saved_empty_agreement_is_distinct_from_preliminary_estimate():
    from scope_guard.domain.llm.commercial_terms import current_commercial_terms

    frozen = source(None, None)
    assert current_commercial_terms(frozen)["source"] == "savedAgreement"
    assert current_commercial_terms(frozen)["additionalCost"] is None
    frozen["document"]["changeOrder"] = None
    terms = current_commercial_terms(frozen)
    assert terms["source"] == "preliminaryEstimate"
    assert terms["additionalCost"] == "240.00" and terms["currency"] == "USD"


@pytest.mark.parametrize("valid", [True, False])
def test_recovered_native_candidate_is_validated_without_extra_calls_or_budget_reset(valid):
    class Store(RecordingStore):
        async def feedback(self, binding, error):
            self.feedbacks.append(error)

    frozen, store = source(), Store()
    binding = Binding(uuid4(), uuid4(), 1, "controlled", "medium", semantic_start=3)
    candidate = output("replies", "220" if valid else "240", "EUR")
    runner = StructuredStageRunner(ProviderGateway(store, None), store)

    async def exercise():
        result = await runner.run(binding, "replies", frozen, {"candidate": json.dumps(candidate)})
        assert "commercialTerms" not in result
        assert result["warm"] == candidate["warm"]

    if valid:
        asyncio.run(exercise())
    else:
        with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
            asyncio.run(exercise())
    assert not store.calls


def test_missing_native_commercial_object_uses_structural_retry():
    store = RecordingStore()

    class Adapter:
        async def request(self, request, timeout):
            value = output("replies")
            if request.semantic_attempt == 1:
                del value["commercialTerms"]
            return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=50)

    async def exercise():
        runner = StructuredStageRunner(ProviderGateway(store, Adapter()), store)
        binding = Binding(uuid4(), uuid4(), 1, "controlled", "medium")
        await runner.run(binding, "replies", source(), {})

    asyncio.run(exercise())
    assert len(store.calls) == 2 and store.calls[0]["rejected"]


def test_intentional_scope_limitation_wrong_monetary_prose_is_observed_after_acceptance():
    store, frozen = RecordingStore(), source()
    value = asyncio.run(run("replies", frozen, [output("replies")], store))
    before = deepcopy(value)
    observations = local_observations(
        Binding(uuid4(), uuid4(), 1, "controlled", "medium"),
        "replies",
        value,
        frozen,
    )
    assert any(o.rule == "commercial_terms" and o.outcome == "finding" for o in observations)
    assert value == before and len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize("exhaust", [False, True])
def test_worker_keeps_accepted_stage_and_publishes_only_after_structured_validation(exhaust):
    store, frozen = RecordingStore(), source()
    frozen["document"]["changeOrder"]["aiValues"] = {}
    saved = deepcopy(frozen["document"])
    operation = {
        "id": uuid4(),
        "epoch": 1,
        "kind": "translate",
        "policy": {"version": "workflow-policy-v1", "model": "controlled"},
        "frozen_input": frozen,
        "input_hash": digest(frozen),
        "deadline_at": datetime.now(UTC) + timedelta(seconds=180),
    }
    for stage in ("replies", "change_order"):
        record = store.review_slot(
            Binding(operation["id"], uuid4(), 1, "controlled", "medium"), stage, 1
        )
        record["stage_key"] = stage

    class Adapter:
        async def request(self, request, timeout):
            stage = request.schema_name.removesuffix("_v1")
            assert stage in ("replies", "change_order")
            value = output(stage)
            if stage == "replies" and (exhaust or request.semantic_attempt == 1):
                value["commercialTerms"]["amount"] = "240"
            if "labels" not in request.schema.get("properties", {}):
                value.pop("labels", None)
            return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=50)

    class Worker(LlmWorker):
        async def publish_document(self, operation, document):
            nonlocal saved
            saved = deepcopy(document)

    async def exercise():
        worker = Worker(
            None, store, StructuredStageRunner(ProviderGateway(store, Adapter()), store)
        )
        # Accepted work from an earlier execution is reused, never generated again.
        await worker.stage(operation, "change_order", frozen)
        if exhaust:
            with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
                await worker.execute(operation)
            assert saved == frozen["document"]
        else:
            await worker.execute(operation)
            assert saved["reply"]["language"] == "es"
            assert saved["changeOrder"]["additionalCost"] == "220"
            assert saved["changeOrder"]["currency"] == "EUR"
            assert saved["reply"]["text"] == "Estos cambios cuestan 240 euros."
        assert "commercialTerms" not in saved
        assert "commercialTerms" not in saved["reply"]
        assert "commercialTerms" not in saved["changeOrder"]
        assert sum(c["request"].schema_name == "change_order_v1" for c in store.calls) == 1
        assert sum(c["request"].schema_name == "replies_v1" for c in store.calls) == (
            3 if exhaust else 2
        )

    asyncio.run(exercise())


def test_completed_old_review_rows_do_not_change_public_status_or_saved_result():
    saved = {"draft": {"draftDocument": {"reply": {"text": "Previously published material"}}}}

    class Store:
        async def get(self, owner, identifier):
            return {
                "id": identifier,
                "status": "succeeded",
                "deadline_at": datetime.now(UTC),
                "frozen_input": {},
                "result": saved,
                "error": None,
            }

        async def steps(self, identifier):
            return [
                {"stage_key": "replies", "status": "accepted"},
                {"stage_key": "replies_review_1", "status": "accepted"},
            ]

    service = LlmOperations(None, Store(), {}, language_selector=None)
    result = asyncio.run(service.status(uuid4(), uuid4()))
    assert result["stages"] == {"replies": "accepted"}
    assert result["result"] == saved and result["status"] == "succeeded"
