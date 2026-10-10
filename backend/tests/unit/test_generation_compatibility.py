import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[3] / "contracts/compatibility/any-640/generation.json"


def test_runtime_normalization_is_immutable_and_serializes_fresh_json():
    from scope_guard.api.generation_output import analysis_to_wire
    from scope_guard.modules.analysis.normalization import parse_analysis

    fixture = json.loads(FIXTURE.read_text(encoding="utf8"))
    result = parse_analysis(fixture["analysisFixture"], "en")
    assert analysis_to_wire(result) == fixture["normalized"]
    with pytest.raises(FrozenInstanceError):
        result.summary = "modified"
    first = analysis_to_wire(result)
    first["citations"].append("forged")
    first["replies"]["warm"] = "forged"
    assert analysis_to_wire(result) == fixture["normalized"]


def test_exact_analysis_reply_and_material_prompt_vectors():
    from scope_guard.infrastructure.llm.prompts.analysis_v1 import analysis_messages, reply_messages
    from scope_guard.infrastructure.llm.prompts.client_materials_v1 import material_messages
    from scope_guard.infrastructure.llm.schemas import ANALYSIS_SCHEMA, MATERIALS_SCHEMA

    fixture = json.loads(FIXTURE.read_text(encoding="utf8"))
    for case in fixture["cases"]:
        assert analysis_messages(case["input"]) == case["messages"]
        for reply in case["replies"]:
            assert (
                reply_messages(
                    {**case["input"], "tone": reply["tone"], "previousReply": "Old reply 😀"}
                )
                == reply["messages"]
            )
    assert (
        material_messages(
            {
                "locale": "ru",
                "clientLanguage": "de",
                "scope": "Five pages.",
                "request": "Add page",
                "analysis": fixture["analysisFixture"],
            }
        )
        == fixture["materials"]
    )
    assert ANALYSIS_SCHEMA == fixture["analysisSchema"]
    assert MATERIALS_SCHEMA == fixture["materialsSchema"]


def test_language_vectors_retain_broad_reply_support_and_pdf_restrictions():
    from scope_guard.infrastructure.llm.language import normalize_language, supported_language

    fixture = json.loads(FIXTURE.read_text(encoding="utf8"))
    for case in fixture["languages"]:
        assert normalize_language(case["raw"]) == case["broad"], case
        assert supported_language(case["raw"]) == case["supported"], case


def test_js_units_and_serialization_keep_unicode_number_and_key_semantics():
    from scope_guard.core.js_compat import stringify, trim, utf16_length

    assert utf16_length("😀") == 2
    assert trim("\ufeff x \ufeff") == "x"
    assert (
        stringify({"b": 2.0, "10": 1, "2": 2, "emoji": "😀"}) == '{"2":2,"10":1,"b":2,"emoji":"😀"}'
    )
