import asyncio

import httpx
import pytest
from fastapi import Body, Request

from scope_guard.core.config import Settings
from scope_guard.main import create_app


def exercise(path, *, method="GET", content=None, headers=None, raise_app_exceptions=False):
    async def run():
        app = create_app(Settings(_env_file=None))

        @app.get("/api/failure")
        async def failure():
            raise RuntimeError("private database content must never escape")

        @app.post("/api/typed")
        async def typed(value: int = Body()):
            return {"value": value}

        @app.post("/api/object")
        async def object_body(request: Request):
            from scope_guard.api.errors import read_json_object

            return await read_json_object(request)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions),
            base_url="http://api.test",
        ) as client:
            return await client.request(method, path, content=content, headers=headers)

    return asyncio.run(run())


def test_unmapped_exception_is_sanitized_existing_error_envelope(caplog):
    response = exercise("/api/failure")
    assert response.status_code == 500
    assert response.json() == {"error": "errors.requestFailed"}
    assert "private database content" not in response.text + caplog.text


def test_unmapped_exception_does_not_reach_server_traceback_logging(caplog):
    response = exercise("/api/failure", raise_app_exceptions=True)
    assert response.status_code == 500
    assert response.json() == {"error": "errors.requestFailed"}
    assert "private database content" not in caplog.text


def test_fastapi_validation_never_leaks_422_detail():
    response = exercise("/api/typed", method="POST", content='"wrong"')
    assert response.status_code == 400
    assert response.json() == {"error": "errors.requestBodyInvalid"}


@pytest.mark.parametrize("body", ["null", "[]", "1", '"text"', "{", ""])
def test_raw_json_parser_rejects_non_objects(body):
    response = exercise("/api/object", method="POST", content=body)
    assert response.status_code == 400
    assert response.json() == {"error": "errors.requestBodyInvalid"}


def test_raw_json_parser_preserves_null_missing_and_unknown_fields():
    response = exercise("/api/object", method="POST", content='{"clientName":null,"extra":1}')
    assert response.status_code == 200
    assert response.json() == {"clientName": None, "extra": 1}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("origin", ["https://evil.test", "null", "https://app.test.evil.test"])
def test_foreign_origin_rejected_before_any_handler(monkeypatch, method, origin):
    monkeypatch.setenv("SCOPE_GUARD_ALLOWED_ORIGINS", '["https://app.test"]')
    response = exercise("/api/failure", method=method, headers={"origin": origin})
    assert response.status_code == 403
    assert response.json() == {"error": "errors.requestFailed"}


def test_allowed_origin_and_originless_clients_can_reach_api(monkeypatch):
    monkeypatch.setenv("SCOPE_GUARD_ALLOWED_ORIGINS", '["https://app.test"]')
    for headers in ({}, {"origin": "https://app.test"}):
        response = exercise("/api/object", method="POST", content="{}", headers=headers)
        assert response.status_code == 200


def test_origin_allowlist_does_not_trust_request_host_or_forwarded_headers(monkeypatch):
    monkeypatch.setenv("SCOPE_GUARD_ALLOWED_ORIGINS", '["https://app.test"]')
    response = exercise(
        "/api/object",
        method="POST",
        content="{}",
        headers={
            "origin": "https://evil.test",
            "host": "evil.test",
            "x-forwarded-host": "evil.test",
        },
    )
    assert response.status_code == 403


def test_missing_allowlist_fails_closed_for_supplied_origin(monkeypatch):
    monkeypatch.delenv("SCOPE_GUARD_ALLOWED_ORIGINS", raising=False)
    assert (
        exercise(
            "/api/object", method="POST", content="{}", headers={"origin": "https://app.test"}
        ).status_code
        == 403
    )


def test_health_contract_untouched_by_business_origin_policy(monkeypatch):
    monkeypatch.setenv("SCOPE_GUARD_ALLOWED_ORIGINS", '["https://app.test"]')
    response = exercise("/health/live", headers={"origin": "https://evil.test"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
