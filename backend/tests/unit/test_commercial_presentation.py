"""Same explicit policy fixtures as the browser builders, including unrelated prose."""

import json
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader
from scope_guard_api.draft_input import parse_editor

from scope_guard.domain.change_orders.presentation import commercial_presentation
from scope_guard.integrations.documents.preparation import prepare_document
from scope_guard.integrations.documents.renderer import render_pdf

FIXTURE = json.loads(
    (Path(__file__).parents[3] / "ci/contracts/commercial-presentation.json").read_text(
        encoding="utf8"
    )
)


@pytest.mark.parametrize("locale", FIXTURE["languages"], ids=lambda x: x["language"])
@pytest.mark.parametrize("rationale", FIXTURE["rationales"], ids=lambda x: x["name"])
def test_shared_commercial_presentation_contract(locale, rationale):
    source = {**FIXTURE["source"], "language": locale["language"], "rationale": rationale["value"]}
    if rationale["name"] == "AI":
        source["aiValues"] = {"rationale": rationale["value"]}
    before = deepcopy(source)
    paid = prepare_document(parse_editor(source))
    assert [row.value for row in paid.commercial] == [locale["effort"], FIXTURE["paidFee"]]
    assert any(row.value == rationale["value"] for row in paid.additional) == bool(
        rationale["value"]
    )
    free_source = {**source, "noAdditionalCharge": True}
    projection = asdict(commercial_presentation(parse_editor(free_source)))
    projection["noCharge"] = projection.pop("no_charge")
    assert projection == FIXTURE["freeProjection"]
    free = prepare_document(parse_editor(free_source))
    labels = dict(free.labels)
    assert [row.value for row in free.commercial] == [locale["effort"], locale["freeFee"]]
    assert not any(row.label == labels["rationale"] for row in free.additional)
    assert free.schedule == source["timelineImpact"]
    assert any(row.label == labels["endDate"] for row in free.additional)
    pdf = render_pdf(free)
    content = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    for field in ("description", "note", "additionalTerms"):
        assert source[field] in content
    restored = json.loads(json.dumps(free_source))
    assert prepare_document(parse_editor(restored)) == free
    assert prepare_document(parse_editor({**restored, "noAdditionalCharge": False})) == paid
    assert source == before
