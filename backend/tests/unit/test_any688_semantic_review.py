"""Structured semantic review decisions are controlled, not real-model accuracy evidence."""

import asyncio
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fixtures.llm_ledger import APPROVED, ReviewLedger
from fixtures.llm_review import PROSE, facts

from scope_guard.domain.llm.runtime import Binding, GatewayFailure, ProviderResponse
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.semantic_review import SemanticReviewer
from scope_guard.integrations.llm.stages import StructuredStageRunner


async def exercise(bad, rule, *, exhaust=False, decision=None, source=None):
    source, store = source or facts(action="regenerate"), ReviewLedger()
    binding = Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "high")
    for attempt in range(1, 4):
        store.review_slot(binding, "reply", attempt)

    class Adapter:
        async def request(self, request, timeout):
            if request.schema_name == "semantic_review_v2":
                payload = json.loads(request.messages[-1]["content"])
                invalid = payload["candidate"]["text"] == bad
                value = (
                    decision
                    if decision is not None
                    else (
                        {
                            "decision": "reject",
                            "violations": [
                                {
                                    "field": "text",
                                    "rule": rule,
                                    "feedback": "Remove the unauthorized commitment.",
                                }
                            ],
                        }
                        if invalid
                        else APPROVED
                    )
                )
            else:
                language = source["selection"]["selectedLanguage"]
                revised = {
                    "en": "The requested additions require a separate estimate "
                    "and approval before work begins.",
                    "ru": "Для этих дополнительных изменений необходимо подготовить "
                    "отдельное предложение и согласовать его до начала работ.",
                    "es": "Antes de comenzar estos cambios adicionales, necesitamos "
                    "una propuesta independiente y su aprobación.",
                }[language]
                if source["analysis"]["verdict"] == "in_scope":
                    revised = "These corrections are covered by our agreement; "
                    revised += "please confirm the details."
                elif source["analysis"]["verdict"] == "borderline":
                    revised = "Please clarify the requested deliverables "
                    revised += "so we can confirm their coverage together."
                value = {
                    "scopePosition": source["analysis"]["verdict"],
                    "text": bad if exhaust or request.semantic_attempt == 1 else revised,
                }
            return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=50)

    runner = StructuredStageRunner(ProviderGateway(store, Adapter()), store)
    saved = deepcopy(source)
    try:
        value = await runner.run(binding, "reply", source, {})
        # A separate diagnostic phase sees the published candidate, without repairs.
        await SemanticReviewer(runner.gateway, store).review(binding, "reply", source, value, 1)
        return value, store, saved, source
    except GatewayFailure as error:
        error.store, error.source, error.saved = store, source, saved
        raise


@pytest.mark.parametrize(
    "bad,rule",
    [
        (
            "Of course, we can add Arrow and email alerts under the existing agreement "
            "at no extra cost. "
            "Send the recipient list and we will get started.",
            "scope_position",
        ),
        (
            "These additions are outside the agreed scope and require approval. "
            "We will deliver everything next week. Please confirm the recipient list.",
            "timeline_commitment",
        ),
    ],
)
def test_actual_candidate_rejection_corrects_only_reply_and_accounts_review(bad, rule):
    value, store, saved, source = asyncio.run(exercise(bad, rule))
    assert value["text"] == bad and source == saved
    assert len(store.calls) == 2
    assert [c["request"].schema_name for c in store.calls] == ["reply_v1", "semantic_review_v2"]
    assert not store.calls[0].get("rejected")
    assert all(c["response"].input_tokens == 100 for c in store.calls)


def test_rejected_review_exhaustion_preserves_saved_manual_materials():
    bad = "We can complete the additional work next week under the existing agreement."
    value, store, saved, source = asyncio.run(exercise(bad, "timeline_commitment", exhaust=True))
    assert value["text"] == bad and source == saved
    assert len(store.calls) == 2 and not store.calls[0].get("rejected")


@pytest.mark.parametrize(
    "decision",
    [
        {
            "decision": "accept",
            "violations": [{"field": "text", "rule": "scope_position", "feedback": "Bad."}],
        },
        {"decision": "accept", "violations": [], "ignore_policy": True},
        {"decision": "reject", "violations": []},
        {
            "decision": "reject",
            "violations": [{"field": "nonexistent", "rule": "scope_position", "feedback": "Bad."}],
        },
    ],
)
def test_invalid_structured_review_fails_closed_without_recursive_repairs(decision):
    with pytest.raises(GatewayFailure, match="providerOutputIncomplete") as caught:
        asyncio.run(
            exercise(
                PROSE["en"] + " Please approve the proposal.", "scope_position", decision=decision
            )
        )
    assert len(caught.value.store.calls) == 2


@pytest.mark.parametrize("locale", ["ru", "en"])
@pytest.mark.parametrize(
    "language,bad",
    [
        ("en", "We will deliver the additional supplier and alerts next week."),
        ("ru", "Мы обязательно завершим подключение нового поставщика на следующей неделе."),
        ("es", "Entregaremos las nuevas funciones del proveedor la próxima semana."),
        ("en", "We will deliver the additional functionality on 2026-11-20."),
        ("ru", "Мы завершим дополнительные работы 20 ноября."),
        ("es", "Entregaremos las funciones adicionales el 20 de noviembre."),
    ],
)
def test_localized_absolute_relative_promises_use_frozen_context_and_correct(locale, language, bad):
    source = facts(language, action="regenerate")
    source["locale"] = locale
    result, store, saved, current = asyncio.run(exercise(bad, "timeline_commitment", source=source))
    assert result["text"] == bad and current == saved
    assert len(store.calls) == 2


@pytest.mark.parametrize(
    "verdict,bad",
    [
        ("in_scope", "These agreed corrections are excluded and need a separate paid agreement."),
        (
            "borderline",
            "These additions are definitely included and we will proceed without approval.",
        ),
        (
            "out_of_scope",
            "We can absorb all the additional effort under the existing fee and start now.",
        ),
    ],
)
def test_actual_scope_claims_are_reviewed_for_every_verdict(verdict, bad):
    source = facts(action="regenerate")
    source["analysis"]["verdict"] = verdict
    result, store, _, _ = asyncio.run(exercise(bad, "scope_position", source=source))
    assert result["text"] == bad and len(store.calls) == 2
    payload = json.loads(store.calls[1]["request"].messages[-1]["content"])
    assert payload["source"]["scopeContext"]["verdict"] == verdict


@pytest.mark.parametrize("locale", ["ru", "en"])
@pytest.mark.parametrize(
    "language,bad",
    [
        (
            "ru",
            "Конечно, мы добавим нового поставщика и уведомления по почте "
            "в рамках существующего договора без дополнительной оплаты.",
        ),
        (
            "es",
            "Por supuesto, añadiremos el nuevo proveedor y los avisos por correo "
            "dentro del contrato actual sin coste adicional.",
        ),
    ],
)
def test_localized_free_work_reversal_is_corrected(locale, language, bad):
    source = facts(language, action="regenerate")
    source["locale"] = locale
    result, store, _, _ = asyncio.run(exercise(bad, "scope_position", source=source))
    assert result["text"] == bad and len(store.calls) == 2


def test_saved_decisions_and_candidate_injection_are_untrusted_review_data():
    source = facts(action="regenerate")
    source["document"]["changeOrder"] = {
        "noAdditionalCharge": True,
        "additionalCost": "333.00",
        "currency": "EUR",
        "estimatedHours": "9.5",
        "timelineImpact": "Delivery subject to approval.",
    }
    candidate = PROSE["en"] + " Please approve the separate proposal."
    result, store, _, _ = asyncio.run(
        exercise(candidate, "scope_position", decision=APPROVED, source=source)
    )
    assert result["text"] == candidate
    review = store.calls[1]["request"]
    payload = json.loads(review.messages[-1]["content"])
    assert payload["source"]["currentCommercialTerms"]["noAdditionalCharge"] is True
    assert payload["source"]["currentCommercialTerms"]["additionalCost"] == "333.00"
    assert review.schema["additionalProperties"] is False
    instructions = " ".join(m["content"] for m in review.messages if m["role"] == "system")
    assert "UNTRUSTED DATA" in instructions and "project endDate alone" in instructions


def test_persisted_review_is_reused_and_cannot_approve_a_different_candidate():
    from scope_guard.integrations.llm.semantic_review import SemanticReviewer

    async def run():
        source, store = facts(), ReviewLedger()
        binding = Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium")
        store.review_slot(binding, "reply", 1)

        class Adapter:
            async def request(self, *_):
                return ProviderResponse(json.dumps(APPROVED), input_tokens=12, output_tokens=4)

        reviewer = SemanticReviewer(ProviderGateway(store, Adapter()), store)
        candidate = {"scopePosition": "out_of_scope", "text": PROSE["en"]}
        await reviewer.review(binding, "reply", source, candidate, 1)
        await reviewer.review(binding, "reply", source, candidate, 1)
        assert len(store.calls) == 1
        with pytest.raises(GatewayFailure, match="workflowVersionUnavailable"):
            await reviewer.review(binding, "reply", source, {**candidate, "text": "Different."}, 1)

    asyncio.run(run())


def test_uncertain_review_corrects_or_exhausts_with_every_call_accounted():
    decision = {
        "decision": "uncertain",
        "violations": [{"field": "text", "rule": "uncertain", "feedback": "Insufficient support."}],
    }
    candidate = PROSE["en"] + " Please review the proposal."
    value, store, saved, source = asyncio.run(exercise(candidate, "uncertain", decision=decision))
    assert value["text"] == candidate and source == saved
    assert len(store.calls) == 2
    assert all(c["response"].output_tokens == 50 for c in store.calls)


def test_review_timeout_retains_uncertain_attempts_without_accepting_materials():
    from scope_guard.integrations.llm.semantic_review import SemanticReviewer

    async def run():
        store, binding = ReviewLedger(), Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium")
        store.review_slot(binding, "reply", 1)

        class Adapter:
            async def request(self, *_):
                raise TimeoutError

        gateway = ProviderGateway(store, Adapter(), sleep=lambda _: asyncio.sleep(0))
        with pytest.raises(GatewayFailure, match="providerOutcomeUnknown"):
            await SemanticReviewer(gateway, store).review(
                binding, "reply", facts(), {"scopePosition": "out_of_scope", "text": PROSE["en"]}, 1
            )
        assert len(store.calls) == 2
        assert all(c["error"]["uncertain"] for c in store.calls)
        assert all(r["status"] != "accepted" for r in store.records.values())
        with pytest.raises(GatewayFailure, match="diagnosticOutcomeUnknown"):
            await SemanticReviewer(gateway, store).review(
                binding, "reply", facts(), {"scopePosition": "out_of_scope", "text": PROSE["en"]}, 1
            )
        assert len(store.calls) == 2

    asyncio.run(run())
