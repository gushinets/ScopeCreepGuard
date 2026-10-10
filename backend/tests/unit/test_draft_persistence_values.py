import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


def fixture():
    return json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())


def test_document_is_immutable_detached_and_serializes_without_optional_nulls():
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.serialization import document_to_wire
    from scope_guard.modules.drafts.values import freeze_object

    data = fixture()
    document = parse_document(data["document"], "en", freeze_object(data["analysis"]))
    with pytest.raises(FrozenInstanceError):
        document.reply.text = "mutated"
    data["document"]["reply"]["text"] = "mutated"
    wire = document_to_wire(document)
    assert wire == fixture()["document"]
    wire["reply"]["generated"]["warm"] = "mutated"
    assert document_to_wire(document) == fixture()["document"]


@pytest.mark.parametrize("field", ["verdict", "summary", "citations", "requestLanguage"])
def test_protected_analysis_cannot_be_changed(field):
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.values import freeze_object

    data = fixture()
    data["document"]["result"][field] = [] if field == "citations" else "changed"
    with pytest.raises(ValueError):
        parse_document(data["document"], "en", freeze_object(data["analysis"]))


def test_document_utf16_text_limit_and_unknown_utf8_size_are_checked_before_discard():
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.values import freeze_object

    data = fixture()
    snapshot = freeze_object(data["analysis"])
    data["document"]["reply"]["text"] = "😀" * 50000
    parse_document(data["document"], "en", snapshot)
    data["document"]["reply"]["text"] += "x"
    with pytest.raises(ValueError):
        parse_document(data["document"], "en", snapshot)
    data = fixture()
    data["document"]["ignored"] = "Ж" * 500000
    with pytest.raises(ValueError):
        parse_document(data["document"], "en", snapshot)


def test_editable_empty_values_and_js_date_and_enum_coercion_are_preserved():
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.serialization import document_to_wire
    from scope_guard.modules.drafts.values import freeze_object

    data = fixture()
    co = data["document"]["changeOrder"]
    co.update(description="", additionalCost="", createdAt="October 6, 2026", currency=[])
    data["document"]["reply"]["tone"] = ["firm"]
    document = parse_document(data["document"], "en", freeze_object(data["analysis"]))
    assert document_to_wire(document) == data["document"]


def test_missing_and_null_are_distinct_and_legacy_payload_is_not_normalized():
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.values import freeze_object, thaw_json

    data = fixture()
    legacy = copy.deepcopy(data["analysis"])
    legacy.pop("requestLanguage")
    legacy["oldUnknown"] = None
    frozen = freeze_object(legacy)
    assert thaw_json(frozen) == legacy
    with pytest.raises(ValueError):
        parse_document(data["document"], "en", frozen)
    data["document"]["result"].pop("requestLanguage")
    parse_document(data["document"], "en", frozen)
    data["document"].pop("clientMaterials")
    with pytest.raises(ValueError):
        parse_document(data["document"], "en", frozen)


def test_preview_counts_utf16_and_can_split_a_surrogate_pair():
    from scope_guard.modules.drafts.serialization import request_preview

    assert request_preview("a" * 158 + "😀") == "a" * 158 + "😀"
    assert request_preview("a" * 156 + "😀" + "b" * 4) == "a" * 156 + "\ud83d…"


def test_frozen_typescript_document_vectors():
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.serialization import document_to_wire
    from scope_guard.modules.drafts.values import freeze_object

    corpus = json.loads(
        (Path(__file__).parents[3] / "contracts/compatibility/any-640/drafts.json").read_text(
            encoding="utf-8"
        )
    )
    base = corpus["base"]
    for vector in corpus["documents"]:
        document = copy.deepcopy(base["document"])
        if vector["path"]:
            keys = vector["path"].split(".")
            node = document
            for key in keys[:-1]:
                node = node[key]
            if vector.get("remove"):
                node.pop(keys[-1], None)
            else:
                node[keys[-1]] = (
                    vector["value"] * vector["repeat"] if "repeat" in vector else vector["value"]
                )
        if vector["valid"]:
            result = parse_document(document, "en", freeze_object(base["analysis"]))
            if "output" in vector:
                assert document_to_wire(result) == vector["output"], vector["name"]
        else:
            with pytest.raises(ValueError):
                parse_document(document, "en", freeze_object(base["analysis"]))


def test_json_byte_limit_is_inclusive_and_counted_after_js_stringify():
    from scope_guard.api.draft_input import size
    from scope_guard.core.js_compat import stringify

    value = {"ignored": "x" * (1_000_000 - len(stringify({"ignored": ""}).encode()))}
    size(value)
    value["ignored"] += "x"
    with pytest.raises(ValueError):
        size(value)


@pytest.mark.parametrize("value", ["10/10/26", "2026-10-10 09:00", "2026-10-10t09:00:00.000z"])
def test_legacy_editor_dates_match_node_date_parse(value):
    from scope_guard.api.draft_input import parse_document
    from scope_guard.modules.drafts.values import freeze_object

    data = fixture()
    data["document"]["changeOrder"]["createdAt"] = value
    parse_document(data["document"], "en", freeze_object(data["analysis"]))
