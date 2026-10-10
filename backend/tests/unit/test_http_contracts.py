import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "contracts/compatibility/any-640/http.json"
UUIDS = {
    "$user": "10000000-0000-4000-8000-000000000001",
    "$project": "10000000-0000-4000-8000-000000000002",
    "$history": "10000000-0000-4000-8000-000000000003",
    "$draft": "10000000-0000-4000-8000-000000000005",
    "$legacyHistory": "10000000-0000-4000-8000-000000000006",
    "$evaluation": "10000000-0000-4000-8000-000000000007",
}


def materialize(value):
    if isinstance(value, str):
        return UUIDS.get(value, value)
    if isinstance(value, list):
        return [materialize(child) for child in value]
    if isinstance(value, dict):
        return {key: materialize(child) for key, child in value.items()}
    return value


def corpus():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_python_response_wrappers_round_trip_every_frozen_json_operation():
    from scope_guard.api.contracts import RESPONSE_MODELS

    observed = set()
    for operation in corpus()["operations"]:
        key = f"{operation['method']} {operation['path']}"
        observed.add(key)
        if "body" in operation:
            body = materialize(operation["body"])
            assert RESPONSE_MODELS[key].model_validate(body).to_wire() == body, key
    assert observed == set(RESPONSE_MODELS)
    assert len(observed) == 21


def test_error_envelopes_keep_existing_localization_codes():
    from scope_guard.api.contracts import ErrorResponse
    from scope_guard.api.errors import ErrorCode

    assert set(ErrorCode) <= set(corpus()["errorCodes"])
    for failure in corpus()["errors"]:
        assert ErrorResponse.model_validate(failure["body"]).to_wire() == failure["body"]


def test_public_request_models_accept_all_frozen_bodies_but_not_snake_aliases():
    from pydantic import ValidationError

    from scope_guard.api.requests import REQUEST_MODELS

    for operation in corpus()["operations"]:
        key = f"{operation['method']} {operation['path']}"
        if key in REQUEST_MODELS:
            body = materialize(operation["request"])
            REQUEST_MODELS[key].model_validate(body)
            if "projectId" in body:
                snake = {**body, "project_id": body["projectId"]}
                del snake["projectId"]
                with pytest.raises(ValidationError):
                    REQUEST_MODELS[key].model_validate(snake)


@pytest.mark.parametrize(
    "pricing,wire,snake",
    [
        ("hourly", "hourlyRate", "hourly_rate"),
        ("fixed", "fixedPrice", "fixed_price"),
    ],
)
def test_public_project_active_price_requires_camel_case(pricing, wire, snake):
    from pydantic import ValidationError

    from scope_guard.api.requests import ProjectBody, ProjectUpdateBody

    body = next(
        op["request"]
        for op in corpus()["operations"]
        if op["method"] == "POST" and op["path"] == "/api/projects"
    )
    body = {**body, "pricingModel": pricing, snake: "100"}
    body.pop(wire, None)
    for model in (ProjectBody, ProjectUpdateBody):
        with pytest.raises(ValidationError):
            model.model_validate(body)


@pytest.mark.parametrize("bad_date", [0, 1, True, "2026-02-30", "2026-1-1", None])
def test_generation_wire_dates_require_valid_iso_strings(bad_date):
    from pydantic import ValidationError

    from scope_guard.api.requests import AnalyzeBody, HistoricalBody

    for model in (AnalyzeBody, HistoricalBody):
        with pytest.raises(ValidationError):
            model.model_validate(
                {"projectId": "$project", "request": "Change", "endDate": bad_date}
            )


def test_jsonl_contract_is_valid_unicode_and_exact_newline():
    from scope_guard.modules.evaluations.schemas import EvaluationJsonlRecord

    operation = next(op for op in corpus()["operations"] if op["path"] == "/api/evaluations/export")
    text = operation["text"]
    records = [
        EvaluationJsonlRecord.model_validate(json.loads(line)).to_wire()
        for line in text.splitlines()
    ]
    assert (
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in records)
        + "\n"
        == text
    )
    assert operation["headers"] == {
        "content-type": "application/x-ndjson; charset=utf-8",
        "content-disposition": 'attachment; filename="scope-creep-evaluations.jsonl"',
    }


@pytest.mark.parametrize(
    "field", ["suggestion", "hasAdditionalWork", "requestLanguage", "estimatedHours", "rationale"]
)
def test_analysis_rejects_present_null_optional_fields_like_typescript(field):
    from pydantic import ValidationError

    from scope_guard.modules.analysis.schemas import AnalysisSnapshot

    body = next(
        op["body"]["result"] for op in corpus()["operations"] if op["path"] == "/api/analyze"
    )
    body = json.loads(json.dumps(body))
    target = body["changeOrder"] if field in {"estimatedHours", "rationale"} else body
    target[field] = None
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(body)


def test_analysis_trims_replies_without_adding_draft_editor_limits():
    from scope_guard.modules.analysis.schemas import AnalysisSnapshot

    body = next(
        op["body"]["result"] for op in corpus()["operations"] if op["path"] == "/api/analyze"
    )
    body = json.loads(json.dumps(body))
    body["replies"]["warm"] = " " + "x" * 100_001 + " "
    result = AnalysisSnapshot.model_validate(body).to_wire()
    assert result["replies"]["warm"] == "x" * 100_001


def test_empty_suggestion_is_omitted_like_typescript():
    from scope_guard.modules.analysis.schemas import AnalysisSnapshot

    body = next(
        op["body"]["result"] for op in corpus()["operations"] if op["path"] == "/api/analyze"
    )
    assert (
        "suggestion" not in AnalysisSnapshot.model_validate({**body, "suggestion": "  "}).to_wire()
    )
