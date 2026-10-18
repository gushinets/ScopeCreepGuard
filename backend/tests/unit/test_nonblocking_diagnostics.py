"""Approved content diagnostics never participate in generator acceptance."""

import asyncio
import json
from uuid import uuid4

import pytest
from fixtures.llm_review import facts, order
from test_llm_review_corrections import RecordingStore, run

from scope_guard.domain.analysis.normalization import parse_snapshot
from scope_guard.domain.analysis.serialization import analysis_to_wire
from scope_guard.domain.drafts.workflow import analysis_matches
from scope_guard.domain.llm.runtime import Binding, GatewayFailure
from scope_guard.integrations.llm.diagnostics import local_observations
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner


@pytest.mark.parametrize(
    "note",
    [
        "This change order is a draft and is not legal advice.",
        "This document is a draft. It is not legal advice.",
    ],
)
def test_exact_retained_low_confidence_notes_are_returned_without_correction(note):
    candidate, source, store = order(), facts(), RecordingStore()
    candidate["note"] = note
    result = asyncio.run(run("change_order", source, [candidate], store))
    assert result["note"] == note
    assert len(store.calls) == 1 and not store.feedbacks
    observations = local_observations(
        Binding(uuid4(), uuid4(), 1, "model", "medium"), "change_order", result, source
    )
    assert observations[0].outcome == "finding"
    assert observations[0].field == "note" and observations[0].confidence < 0.75
    assert note not in json.dumps([o.model_dump(mode="json") for o in observations])


def test_exact_retained_translated_hours_parser_mismatch_is_diagnostic():
    source, store = facts("en", "translate"), RecordingStore()
    source["selection"]["selectedLanguage"] = "es"
    source["document"]["reply"]["text"] = "12 additional hours"
    source["document"]["reply"]["generated"] = dict.fromkeys(
        ("warm", "neutral", "firm"), "12 additional hours"
    )
    candidate = {
        "scopePosition": "out_of_scope",
        **dict.fromkeys(("warm", "neutral", "firm"), "12 horas adicionales"),
    }
    result = asyncio.run(run("replies", source, [candidate], store))
    assert result == candidate and len(store.calls) == 2
    observations = local_observations(
        Binding(uuid4(), uuid4(), 1, "model", "medium"), "replies", result, source
    )
    assert any(o.outcome == "finding" for o in observations)


def test_malformed_generator_structure_remains_a_real_failure():
    store = RecordingStore()
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(
            run(
                "replies",
                facts(),
                [{"scopePosition": "out_of_scope", "warm": "missing tones"}],
                store,
            )
        )
    assert len(store.calls) == 3
    assert all(c["request"].schema_name == "replies_v1" for c in store.calls)


def test_malformed_generator_json_is_never_success():
    from scope_guard.domain.llm.runtime import ProviderResponse

    store = RecordingStore()

    class Adapter:
        async def request(self, request, timeout):
            return ProviderResponse("{broken JSON", input_tokens=12, output_tokens=4)

    async def exercise():
        binding = Binding(uuid4(), uuid4(), 1, "model", "medium")
        await StructuredStageRunner(ProviderGateway(store, Adapter()), store).run(
            binding, "replies", facts(), {}
        )

    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(exercise())
    assert len(store.calls) == 3
    assert all(c["request"].schema_name == "replies_v1" for c in store.calls)


def test_pricing_changes_preserve_classification_but_scope_changes_do_not():
    project = {
        "scope": "frozen scope",
        "industry": "Development",
        "hourlyRate": "30",
        "currency": "USD",
    }
    run = {"status": "succeeded", "requestText": "request", "projectSnapshot": project}
    assert analysis_matches(run, "request", {**project, "hourlyRate": "80", "currency": "EUR"})
    assert not analysis_matches(run, "request", {**project, "scope": "changed scope"})
    assert not analysis_matches(run, "new request", project)


def test_absent_agreement_and_original_estimate_round_trip():
    from integration.test_llm_pipeline import output

    source = output("analysis_v1", "en", "en")
    source.update(clientLanguage="en", replies=output("replies_v1", "en", "en"))
    source["replies"].pop("scopePosition")
    source["estimate"] = {
        k: source.pop(k) for k in ("estimatedHours", "additionalCost", "currency")
    }
    source["changeOrder"] = None
    wire = analysis_to_wire(parse_snapshot(source))
    assert wire["changeOrder"] is None and wire["estimate"]["additionalCost"] == "240.00"
