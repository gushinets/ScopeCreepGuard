"""Three review regressions exercised through the real native structured runner."""

import asyncio
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fixtures.llm_review import PROSE, facts, order

from scope_guard.domain.llm.runtime import Binding, GatewayFailure, ProviderResponse
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner, validate_stage, validate_text
from scope_guard.services.llm.worker import LlmWorker


class RecordingStore:
    def __init__(self):
        self.calls, self.feedbacks = [], []

    async def reserve(self, request, transport_attempt):
        self.calls.append({"request": request, "transport": transport_attempt})
        return len(self.calls) - 1

    async def complete(self, identifier, response=None, error=None):
        self.calls[identifier].update(response=response, error=error)

    async def checkpoint(self, *_):
        pass

    async def feedback(self, binding, error):
        self.feedbacks.append(error)
        self.calls[-1]["rejected"] = True


async def run(stage, source, outputs, store):
    class Adapter:
        async def request(self, request, timeout):
            index = len(store.calls) - 1
            return ProviderResponse(
                json.dumps(outputs[min(index, len(outputs) - 1)], ensure_ascii=False),
                input_tokens=100,
                output_tokens=50,
            )

    return await StructuredStageRunner(ProviderGateway(store, Adapter()), store).run(
        Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "high" if stage == "reply" else "medium"),
        stage,
        source,
        {},
    )


@pytest.mark.parametrize("language", ["en", "ru", "es"])
def test_real_document_labels_pass_once_without_correction(language):
    store = RecordingStore()
    result = asyncio.run(run("change_order", facts(language), [order(language)], store))
    assert result["labels"] == order(language)["labels"]
    assert len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize(
    "label",
    [
        "Дополнительные условия",
        "Condiciones comerciales adicionales",
        "Дата",
        "Fecha",
        "Payment / Pago",
        "Date de signature",
        "Additional terms y fecha",
        "Schedule impact y fecha",
        "Schedule impact / Изменение согласованных сроков проекта",
        "Additional terms / Condiciones comerciales adicionales",
    ],
)
def test_confident_group_cannot_excuse_foreign_or_mixed_label(label):
    value = order()
    value["labels"]["scheduleImpact"] = label
    with pytest.raises(ValueError, match=r"labels.scheduleImpact.language"):
        validate_stage("change_order", value, facts())


def test_empty_labels_and_ordinary_uncertain_prose_remain_invalid():
    value = order()
    value["labels"]["scheduleImpact"] = " "
    with pytest.raises(ValueError, match=r"labels.scheduleImpact.required"):
        validate_stage("change_order", value, facts())
    with pytest.raises(ValueError, match="language"):
        validate_text("summary", "Schedule impact", "en", facts(), analysis=True)
    value = order()
    value["labels"]["introduction"] = "Requested change"
    with pytest.raises(ValueError, match=r"labels.introduction.language"):
        validate_stage("change_order", value, facts())


@pytest.mark.parametrize("first", [PROSE["en"], "  " + PROSE["en"].replace(" ", "\n  ") + " "])
def test_duplicate_regeneration_corrects_only_reply_and_records_rejection(first):
    store = RecordingStore()
    revised = "The requested additions require a separate estimate and approval before work begins."
    source = facts(action="regenerate", tone="firm")
    saved = deepcopy(source)
    value = asyncio.run(
        run(
            "reply",
            source,
            [{"scopePosition": "out_of_scope", "text": text} for text in (first, revised)],
            store,
        )
    )
    assert value["text"] == revised
    assert source == saved
    assert [c["request"].semantic_attempt for c in store.calls] == [1, 2]
    assert all(c["request"].schema_name == "reply_v1" for c in store.calls)
    assert store.calls[0]["rejected"]
    feedback = json.dumps(store.calls[1]["request"].messages)
    assert "text.unchanged_reply" in feedback and "new formulation" in feedback


def test_duplicate_exhaustion_is_bounded_and_preserves_frozen_materials():
    store, source = RecordingStore(), facts(action="regenerate")
    saved = deepcopy(source)
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(
            run("reply", source, [{"scopePosition": "out_of_scope", "text": PROSE["en"]}], store)
        )
    assert source == saved and len(store.calls) == 3
    assert all(c["rejected"] and c["response"].output_tokens == 50 for c in store.calls)


@pytest.mark.parametrize("status", ["pending", "accepted"])
def test_old_prompt_version_fails_before_runner_or_accepted_output_reuse(status):
    class Store:
        async def steps(self, *_):
            return [
                {
                    "stage_key": "reply",
                    "prompt_version": "workflow-v1",
                    "schema_version": "stage-v1",
                    "status": status,
                }
            ]

    worker = LlmWorker(None, Store(), None)
    with pytest.raises(GatewayFailure, match="workflowVersionUnavailable"):
        asyncio.run(
            worker.stage(
                {"id": uuid4(), "policy": {"version": "workflow-policy-v1"}}, "reply", facts()
            )
        )


@pytest.mark.parametrize("stage", ["analysis", "replies", "reply", "change_order", "estimate"])
@pytest.mark.parametrize("tone", ["warm", "neutral", "firm"])
def test_stage_request_preserves_relevant_tone_commercial_and_language_rules(stage, tone):
    source, store = (
        facts("es", "regenerate" if stage == "reply" else "check", tone),
        RecordingStore(),
    )
    if stage == "analysis":
        value = {
            **source["analysis"],
            "confidence": 95,
            "summary": PROSE["en"],
            "reasoning": PROSE["en"],
            "suggestion": PROSE["en"],
        }
    elif stage == "replies":
        value = {
            "scopePosition": "out_of_scope",
            **dict.fromkeys(("warm", "neutral", "firm"), PROSE["es"]),
        }
    elif stage == "reply":
        value = {
            "scopePosition": "out_of_scope",
            "text": PROSE["es"] + " Podemos preparar esa propuesta para su revisión.",
        }
    elif stage == "estimate":
        value = {
            "scopePosition": "out_of_scope",
            "estimatedHours": 8,
            "additionalCost": "240.00",
            "currency": "USD",
            "rationale": PROSE["es"],
        }
    else:
        value = order("es")
    asyncio.run(run(stage, source, [value], store))
    request = store.calls[0]["request"]
    instructions = "\n".join(m["content"] for m in request.messages if m["role"] == "system")
    assert "Return only the final reply" not in instructions and "@@" not in instructions
    assert "native schema" in instructions
    assert f"All prose must be in {'en' if stage == 'analysis' else 'es'}" in instructions
    assert request.schema["additionalProperties"] is False
    assert request.binding.effort == ("high" if stage == "reply" else "medium")
    tones = {
        "warm": "warm, calm, professional, and confidently helpful",
        "neutral": "neutral, calm, factual, and professional",
        "firm": "additional out-of-scope work will not begin",
    }
    for name, instruction in tones.items():
        assert (instruction in instructions) == (
            stage == "replies" or stage == "reply" and name == tone
        )
    for rule in (
        "hourly rate",
        "original project price",
        "preliminary and user-editable",
        "empty currency",
    ):
        assert (rule in instructions) == (stage in ("analysis", "estimate"))
    assert ("not legal advice" in instructions) == (stage == "change_order")
    assert ("IN_SCOPE:" in instructions) == (stage == "analysis")


@pytest.mark.parametrize("stage", ["replies", "change_order"])
def test_translation_stage_request_preserves_saved_materials_without_estimating(stage):
    source, store = facts("es", "translate"), RecordingStore()
    source["document"]["reply"].update(language="es")
    value = (
        order("es")
        if stage == "change_order"
        else {
            "scopePosition": "out_of_scope",
            **dict.fromkeys(("warm", "neutral", "firm"), PROSE["es"]),
        }
    )
    asyncio.run(run(stage, source, [value], store))
    instructions = "\n".join(
        m["content"] for m in store.calls[0]["request"].messages if m["role"] == "system"
    )
    assert "including manual edits" in instructions
    assert "Do not reassess" in instructions
    assert "hourly rate" not in instructions and "IN_SCOPE:" not in instructions
    assert "confidently helpful" not in instructions
