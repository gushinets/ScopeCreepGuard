import asyncio
import copy
import hmac
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from scope_guard.infrastructure.auth.draft_proofs import DraftProofs, decode, encode
from scope_guard.modules.analysis.domain import (
    ABSENT,
    DraftProofBinding,
    DraftProofClaims,
    freeze,
    thaw,
)
from scope_guard.modules.analysis.normalization import parse_analysis, parse_materials
from scope_guard.modules.change_orders.schemas import LABEL_KEYS

FIXTURE = json.loads(
    (Path(__file__).parents[3] / "contracts/compatibility/any-640/generation.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("locale", ["en", "ru"])
@pytest.mark.parametrize(
    "language", ["ru", "en", "es", "de", "pt-BR", "es-419", "ar", "he", "ja", "zh-Hant-TW", None]
)
def test_language_matrix_normalization_and_verbatim_citations(locale, language):
    raw = copy.deepcopy(FIXTURE["analysisFixture"])
    raw["citations"] = [" Русский 😀 scope "]
    raw["changeOrderLabels"] = {key: " label " for key in LABEL_KEYS}
    raw["clientLanguage"] = language
    result = parse_analysis(raw, locale)
    assert result.client_language == (language or locale)
    assert result.citations == (" Русский 😀 scope ",)
    assert result.change_order_labels.values[0][1] == "label"
    with pytest.raises(FrozenInstanceError):
        result.replies.warm = "changed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", -1),
        ("confidence", 101),
        ("confidence", 0.5),
        ("confidence", True),
        ("summary", " "),
        ("citations", [1]),
        ("suggestion", None),
        ("hasAdditionalWork", None),
        ("requestLanguage", None),
        ("replies", None),
        ("changeOrder", None),
    ],
)
def test_malformed_analysis_rejected(field, value):
    with pytest.raises(ValueError):
        parse_analysis({**FIXTURE["analysisFixture"], field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("estimatedHours", None),
        ("estimatedHours", -1),
        ("estimatedHours", True),
        ("currency", None),
        ("currency", "GBP"),
        ("rationale", None),
    ],
)
def test_invalid_commercial_output_rejected(field, value):
    raw = copy.deepcopy(FIXTURE["analysisFixture"])
    raw["changeOrder"][field] = value
    with pytest.raises(ValueError):
        parse_analysis(raw)


def test_normalization_keeps_legacy_tolerance_and_no_extra_pricing_formula():
    raw = copy.deepcopy(FIXTURE["analysisFixture"])
    raw["suggestion"] = " \ufeff "
    raw["changeOrder"].pop("currency")
    result = parse_analysis(raw)
    assert result.estimate_valid is True and result.suggestion == ABSENT
    raw["changeOrder"]["estimatedHours"] = 0
    assert parse_analysis(raw).estimate_valid is False
    materials = parse_materials(
        {
            "clientLanguage": "es",
            "replies": {"warm": " Hola ", "neutral": " Extra ", "firm": " Aprueba "},
            "changeOrder": {
                "description": " Extra ",
                "timelineImpact": " Dos días ",
                "rationale": "",
                "note": " Borrador ",
                "additionalCost": "forged",
            },
        }
    )
    assert materials.replies.warm == " Hola " and materials.change_order.rationale == ""
    assert not hasattr(materials.change_order, "additional_cost")


def proof_setup():
    binding = DraftProofBinding("owner", "00000000-0000-0000-0000-000000000000", "request 😀", "en")
    claims = DraftProofClaims(
        binding,
        parse_analysis(FIXTURE["analysisFixture"]),
        freeze(FIXTURE["projectSnapshotFixture"]),
    )
    return DraftProofs("synthetic", lambda: 1000), binding, claims


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", "other"),
        ("iss", "foreign"),
        ("aud", "foreign"),
        ("iat", 1001),
        ("iat", 1000.5),
        ("exp", 1000),
        ("exp", 4601),
        ("nbf", 1001),
        ("sub", "other"),
        ("userId", "other"),
        ("projectId", "other"),
        ("request", "other"),
        ("locale", "ru"),
        ("projectSnapshot", None),
    ],
)
def test_proof_claim_guards_on_valid_signatures(key, value):
    adapter, binding, claims = proof_setup()
    header, payload, _ = adapter.issue(claims).split(".")
    raw = json.loads(decode(payload))
    raw[key] = value
    payload = encode(json.dumps(raw).encode())
    message = header + "." + payload
    signature = hmac.digest(
        hmac.digest(b"synthetic", b"scg-draft-proof-v1", "sha256"), message.encode(), "sha256"
    )
    with pytest.raises(ValueError):
        adapter.verify(message + "." + encode(signature), binding)


def test_proof_tampering_secret_and_detached_json():
    adapter, binding, claims = proof_setup()
    token = adapter.issue(claims)
    assert adapter.verify(token, binding) == claims
    with pytest.raises(ValueError):
        DraftProofs("different", lambda: 1000).verify(token, binding)
    header, payload, signature = token.split(".")
    raw = json.loads(decode(payload))
    raw["request"] = "tampered"
    with pytest.raises(ValueError):
        adapter.verify(header + "." + encode(json.dumps(raw).encode()) + "." + signature, binding)
    changed = thaw(claims.project_snapshot)
    changed["name"] = "changed"
    assert thaw(claims.project_snapshot)["name"] != "changed"


def test_year_zero_leap_utc_normalization():
    from scope_guard.modules.change_orders.estimation import calendar_day, project_timing

    assert calendar_day("0000-02-29") == calendar_day("1900-03-01")
    assert project_timing("2024-02-28", "2024-03-01", "2024-02-29T23:00:00Z")["durationDays"] == 2


def test_disconnect_cancels_and_awaits_work():
    from scope_guard.api.cancellation import run_connected

    async def run():
        entered, cleaned = asyncio.Event(), asyncio.Event()

        class Request:
            async def receive(self):
                await entered.wait()
                return {"type": "http.disconnect"}

        async def work():
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        with pytest.raises(asyncio.CancelledError):
            await run_connected(Request(), work())
        assert cleaned.is_set()

    asyncio.run(run())


def test_legacy_timestamp_parsing_matches_frozen_javascript_vectors():
    from scope_guard.core.js_compat import date_parse_finite

    vectors = json.loads(
        (
            Path(__file__).parents[3] / "contracts/compatibility/any-640/generation-dates.json"
        ).read_text(encoding="utf-8")
    )
    for vector in vectors:
        assert date_parse_finite(vector["value"]) == vector["valid"], vector
