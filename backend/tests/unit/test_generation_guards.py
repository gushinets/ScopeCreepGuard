import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parents[3] / "contracts/compatibility/any-640/generation.json"


def test_proof_roundtrip_binding_and_expiry():
    from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
    from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
    from scope_guard.modules.analysis.normalization import parse_snapshot

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    binding = DraftProofBinding("user", "11111111-1111-4111-8111-111111111111", "request", "en")
    clock = [1000.0]
    adapter = DraftProofs("synthetic-secret", lambda: clock[0])
    claims = DraftProofClaims(
        binding,
        parse_snapshot(fixture["analysisFixture"], "en"),
        freeze(fixture["projectSnapshotFixture"]),
    )
    token = adapter.issue(claims)
    assert adapter.verify(token, binding) == claims
    with pytest.raises(ValueError):
        adapter.verify(token, DraftProofBinding("other", binding.project_id, "request", "en"))
    clock[0] = 4600
    with pytest.raises(ValueError):
        adapter.verify(token, binding)


def test_shared_rolling_window():
    from scope_guard.infrastructure.llm.rate_limit import GenerationLimiter

    limiter = GenerationLimiter()
    assert all(limiter.allow("user", 1000) for _ in range(10))
    assert not limiter.allow("user", 60999)
    assert limiter.allow("other", 1000)
    assert limiter.allow("user", 61000)


def test_ordered_inputs_preserve_omission_and_null():
    from scope_guard.api.generation_input import parse_analyze, parse_materials
    from scope_guard.modules.analysis.domain import ABSENT, GenerationError

    with pytest.raises(GenerationError, match="clientLanguageUnsupported"):
        parse_analyze({"documentLanguage": None})
    command = parse_analyze({"projectId": " id ", "request": " x😀 "})
    assert (command.project_id, command.request) == ("id", "x😀")
    command = parse_materials({"projectId": " id ", "request": " x ", "clientLanguage": "es"})
    assert command.request == " x " and command.analysis == ABSENT
    with pytest.raises(GenerationError, match="requestBodyInvalid"):
        parse_materials({"projectId": "id", "request": "x", "historyId": None})
