"""Optional review executes native contracts through a controlled provider only."""

import asyncio
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fixtures.llm_ledger import ReviewLedger
from fixtures.llm_review import facts

from scope_guard.core.config import Settings
from scope_guard.domain.llm.runtime import PROMPT_VERSION, ProviderResponse, digest
from scope_guard.integrations.llm.diagnostics import execute_diagnostics
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner


def test_environment_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("SCOPE_GUARD_LLM_SEMANTIC_REVIEW_ENABLED", raising=False)
    assert Settings(_env_file=None).llm_semantic_review_enabled is False
    monkeypatch.setenv("SCOPE_GUARD_LLM_SEMANTIC_REVIEW_ENABLED", "true")
    assert Settings(_env_file=None).llm_semantic_review_enabled is True


class DiagnosticLedger(ReviewLedger):
    def __init__(self, frozen=True):
        super().__init__()
        self.parent_id, self.operation_id = uuid4(), uuid4()
        self.source = {
            "id": uuid4(),
            "stage_key": "reply",
            "status": "accepted",
            "prompt_version": PROMPT_VERSION,
            "schema_version": "stage-v1",
            "accepted_result": {
                "scopePosition": "out_of_scope",
                "text": "Separate approval is required.",
            },
        }
        self.parent = {
            "id": self.parent_id,
            "kind": "regenerate",
            "frozen_input": facts(action="regenerate"),
        }
        self.operation = {
            "id": self.operation_id,
            "owner_id": uuid4(),
            "epoch": 1,
            "deadline_at": None,
            "policy": {"model": "controlled"},
            "frozen_input": {"contract": "diagnostics-v1", "parentId": str(self.parent_id)},
        }
        if frozen is not None:
            self.operation["frozen_input"]["semanticReview"] = {
                "enabled": frozen,
                "promptVersion": "semantic-review-v1",
                "schemaVersion": "semantic-review-v2",
                "sources": {
                    "reply": {
                        "stepId": str(self.source["id"]),
                        "outputHash": digest(self.source["accepted_result"]),
                        "promptVersion": PROMPT_VERSION,
                        "schemaVersion": "stage-v1",
                    }
                },
            }
        self.records["reply_diagnostic"] = {
            "id": uuid4(),
            "stage_key": "reply_diagnostic",
            "status": "pending",
            "prompt_version": PROMPT_VERSION,
            "input_hash": None,
        }
        if frozen:
            from scope_guard.domain.llm.runtime import Binding

            record = self.review_slot(
                Binding(self.operation_id, uuid4(), 1, "controlled", "medium"), "reply", 1
            )
            record.update(prompt_version="semantic-review-v1", schema_version="semantic-review-v2")

    async def get(self, owner, identifier):
        assert identifier == self.parent_id
        return self.parent

    async def steps(self, identifier):
        return [self.source] if identifier == self.parent_id else list(self.records.values())

    async def diagnostic_result(self, binding, value):
        await self.accept(binding, value)

    async def finish_diagnostics(self, operation, result=None):
        self.result = result


async def exercise(store, runtime, decision=None, error=None):
    class Adapter:
        async def request(self, request, timeout):
            assert request.schema_name == "semantic_review_v2"
            if error:
                raise error
            return ProviderResponse(
                json.dumps(decision or {"decision": "accept", "violations": []}),
                model="actual-controlled",
                input_tokens=10,
                output_tokens=5,
            )

    runner = StructuredStageRunner(
        ProviderGateway(store, Adapter()), store, semantic_review_enabled=runtime
    )
    await execute_diagnostics(runner, store.operation)
    return store.result["reviews"][0]


@pytest.mark.parametrize(
    "frozen,runtime", [(None, True), (False, True), (True, False), (None, False)]
)
def test_disabled_or_historical_jobs_keep_local_observations_without_calls(frozen, runtime):
    store = DiagnosticLedger(frozen)
    result = asyncio.run(exercise(store, runtime))
    assert result["outcome"] == "skipped_disabled"
    assert not store.calls
    assert store.records["reply_diagnostic"]["accepted_result"]["observations"]


@pytest.mark.parametrize(
    "decision,outcome",
    [
        ({"decision": "accept", "violations": []}, "completed_clean"),
        (
            {
                "decision": "reject",
                "violations": [
                    {"field": "text", "rule": "facts", "feedback": "Unsupported statement."}
                ],
            },
            "completed_findings",
        ),
    ],
)
def test_enabled_review_persists_findings_and_reuses_accepted_stage(decision, outcome):
    store = DiagnosticLedger()
    original = deepcopy((store.parent, store.source))
    result = asyncio.run(exercise(store, True, decision))
    assert result["outcome"] == outcome
    assert result["outputHash"] == digest(store.source["accepted_result"])
    assert len(store.calls) == 1
    assert (store.parent, store.source) == original
    replay = asyncio.run(exercise(store, True))
    assert replay == result
    assert "Unsupported statement." not in json.dumps(result)
    assert len(store.calls) == 1


def test_incompatible_reviewer_preserves_local_work():
    store = DiagnosticLedger()
    store.operation["frozen_input"]["semanticReview"]["promptVersion"] = "future"
    assert asyncio.run(exercise(store, True))["outcome"] == "unavailable_version"
    assert not store.calls
    assert store.records["reply_diagnostic"]["accepted_result"]["observations"]


def test_provider_failure_is_terminal_diagnostic_only():
    store = DiagnosticLedger()
    assert (
        asyncio.run(exercise(store, True, error=RuntimeError("private provider error")))["outcome"]
        == "failed"
    )
    assert asyncio.run(exercise(store, True))["outcome"] == "failed"
    assert len(store.calls) == 1
    assert "private provider error" not in json.dumps(store.result)


@pytest.mark.parametrize("stage", ["replies", "change_order", "estimate"])
def test_enabled_review_supports_existing_material_stages(stage):
    from integration.test_llm_pipeline import output

    store = DiagnosticLedger()
    store.source.update(stage_key=stage, accepted_result=output(stage + "_v1", "en", "en"))
    for record in store.records.values():
        record["stage_key"] = record["stage_key"].replace("reply_", stage + "_")
    store.records = {record["stage_key"]: record for record in store.records.values()}
    source_config = store.operation["frozen_input"]["semanticReview"]["sources"].pop("reply")
    source_config["outputHash"] = digest(store.source["accepted_result"])
    store.operation["frozen_input"]["semanticReview"]["sources"][stage] = source_config
    result = asyncio.run(exercise(store, True))
    assert result["outcome"] == "completed_clean"
    assert len(store.calls) == 1
