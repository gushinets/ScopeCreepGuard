from dataclasses import FrozenInstanceError

import pytest
from fastapi.testclient import TestClient

from scope_guard.api.errors import ApiError
from scope_guard.core.config import Settings
from scope_guard.core.contracts import Industry, Verdict

HISTORY_ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({}, "errors.historyDateInvalid"),
        ({"date": "2026-1-01"}, "errors.historyDateInvalid"),
        ({"date": "2026-02-31", "request": " "}, "errors.requestRequired"),
        (
            {"date": "2026-02-31", "request": " x ", "verdict": "other"},
            "errors.verdictInvalid",
        ),
        (
            {
                "date": "2026-02-31",
                "request": " x ",
                "verdict": "in_scope",
                "summary": " ",
            },
            "errors.summaryRequired",
        ),
    ],
)
def test_history_parser_preserves_legacy_validation_order(body, code):
    from scope_guard.api.history_input import parse_history

    with pytest.raises(ApiError) as caught:
        parse_history(body)
    assert caught.value.code.value == code


def test_history_parser_accepts_shape_only_date_and_returns_frozen_trimmed_value():
    from scope_guard.api.history_input import parse_history

    value = parse_history(
        {
            "date": "2026-02-31",
            "request": "\u00a0Add a page\ufeff",
            "verdict": "out_of_scope",
            "summary": "  Extra work  ",
            "ignored": True,
        }
    )
    assert value.date == "2026-02-31"
    assert value.request == "Add a page"
    assert value.summary == "Extra work"
    with pytest.raises(FrozenInstanceError):
        value.summary = "changed"


def test_history_encoded_slash_id_preserves_auth_then_malformed_id_mapping():
    from scope_guard.api.dependencies import current_owner
    from scope_guard.main import create_app

    app = create_app(Settings(_env_file=None))
    client = TestClient(app)
    path = "/api/projects/a%2Fb/history"
    response = client.post(path, content="[", follow_redirects=False)
    assert response.status_code == 401
    assert response.json() == {"error": "errors.authRequired"}

    app.dependency_overrides[current_owner] = lambda: {"id": HISTORY_ID}
    response = client.post(path, content="[", follow_redirects=False)
    assert response.status_code == 500
    assert response.json() == {"error": "errors.requestFailed"}


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({}, 404, "errors.evaluationHistoryNotFound"),
        ({"historyEntryId": "bad"}, 404, "errors.evaluationHistoryNotFound"),
        (
            {"historyEntryId": HISTORY_ID, "accuracy": "bad", "aiReasoning": " "},
            400,
            "errors.evaluationReasoningRequired",
        ),
        (
            {"historyEntryId": HISTORY_ID, "accuracy": "bad", "aiReasoning": "why"},
            400,
            "errors.evaluationLabelInvalid",
        ),
        (
            {
                "historyEntryId": HISTORY_ID,
                "accuracy": "correct",
                "aiReasoning": "why",
                "humanVerdict": None,
            },
            400,
            "errors.evaluationLabelInvalid",
        ),
        (
            {"historyEntryId": HISTORY_ID, "accuracy": "wrong", "aiReasoning": "why"},
            400,
            "errors.evaluationLabelInvalid",
        ),
    ],
)
def test_evaluation_parser_preserves_legacy_validation_order(body, status, code):
    from scope_guard.api.evaluation_input import parse_evaluation

    with pytest.raises(ApiError) as caught:
        parse_evaluation(body)
    assert (caught.value.status, caught.value.code.value) == (status, code)


@pytest.mark.parametrize(
    ("accuracy", "human", "ai", "resolved"),
    [
        ("correct", None, Verdict.out_of_scope, Verdict.out_of_scope),
        ("debatable", None, Verdict.borderline, None),
        ("wrong", "in_scope", Verdict.out_of_scope, Verdict.in_scope),
    ],
)
def test_evaluation_resolution(accuracy, human, ai, resolved):
    from scope_guard.api.evaluation_input import parse_evaluation
    from scope_guard.modules.evaluations.use_cases import resolve_human_verdict

    body = {
        "historyEntryId": HISTORY_ID,
        "accuracy": accuracy,
        "aiReasoning": "  reason  ",
        **({"humanVerdict": human} if human is not None else {}),
    }
    label = parse_evaluation(body)
    assert label.ai_reasoning == "reason"
    assert resolve_human_verdict(label, ai) == resolved


def test_wrong_evaluation_rejects_the_ai_verdict():
    from scope_guard.api.evaluation_input import parse_evaluation
    from scope_guard.modules.evaluations.use_cases import EvaluationError, resolve_human_verdict

    label = parse_evaluation(
        {
            "historyEntryId": HISTORY_ID,
            "accuracy": "wrong",
            "aiReasoning": "reason",
            "humanVerdict": "borderline",
        }
    )
    with pytest.raises(EvaluationError) as caught:
        resolve_human_verdict(label, Verdict.borderline)
    assert caught.value.code == "errors.evaluationLabelInvalid"


def test_jsonl_serializer_has_exact_utf8_bytes_field_order_and_newline():
    from scope_guard.domain.evaluations.domain import EvaluationExport
    from scope_guard.domain.evaluations.serialization import serialize_jsonl

    row = EvaluationExport(
        scope="Сайт",
        request="Добавить страницу",
        ai_verdict=Verdict.out_of_scope,
        human_verdict=None,
        ai_reasoning="Это новая работа",
        industry=Industry.Development,
    )
    assert serialize_jsonl(()) == b""
    assert (
        serialize_jsonl((row,))
        == (
            '{"scope":"Сайт","request":"Добавить страницу","ai_verdict":"OUT_OF_SCOPE",'
            '"human_verdict":null,"ai_reasoning":"Это новая работа",'
            '"project_type":"development"}\n'
        ).encode()
    )


@pytest.mark.parametrize(("production", "secure"), [(False, False), (True, True)])
def test_locale_cookie_contract_in_development_and_production(production, secure):
    from scope_guard.main import create_app

    client = TestClient(create_app(Settings(_env_file=None, production=production)))
    response = client.post("/api/locale", json={"locale": "en"})
    assert response.status_code == 200 and response.json() == {"ok": True}
    cookie = response.headers["set-cookie"]
    assert "locale=en" in cookie
    assert "Max-Age=31536000" in cookie and "Expires=" in cookie
    assert "Path=/" in cookie and "SameSite=lax" in cookie
    assert "HttpOnly" not in cookie
    assert ("Secure" in cookie) is secure


def test_locale_rejects_invalid_body_and_value():
    from scope_guard.main import create_app

    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.post("/api/locale", content="[").json() == {"error": "errors.requestBodyInvalid"}
    response = client.post("/api/locale", json={"locale": "de"})
    assert response.status_code == 400
    assert response.json() == {"error": "errors.localeInvalid"}
