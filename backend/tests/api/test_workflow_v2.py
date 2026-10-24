import pytest
from fastapi.testclient import TestClient
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings


def test_explicit_edit_contract_preserves_omission_and_clear_and_forbids_mixed_payloads():
    from pydantic import ValidationError
    from scope_guard_api.schemas.workflow import SaveWorkingDraft

    identity = {"expectedRevision": "1", "operationId": "22222222-2222-4222-8222-222222222222"}
    parsed = SaveWorkingDraft.model_validate({**identity, "patch": {"reply.text": ""}})
    assert parsed.to_wire() == {**identity, "patch": {"reply.text": ""}}
    for payload in (
        {},
        {"patch": None},
        {"patch": {}},
        {"patch": {"analysisIsStale": False}},
        {"patch": {"reply.text": None}},
        {"changes": {}, "patch": {"reply.text": "text"}},
        {"changes": None, "patch": {"reply.text": "text"}},
    ):
        with pytest.raises(ValidationError):
            SaveWorkingDraft.model_validate({**identity, **payload})


def test_v2_requires_authentication_and_retires_unsafe_legacy_routes():
    app = create_app(Settings(_env_file=None, workflow_v2=True))
    with TestClient(app) as client:
        assert client.get("/api/v2/projects").status_code == 401
        assert (
            client.post(
                "/api/v2/drafts/11111111-1111-4111-8111-111111111111/agreement",
                json={
                    "operationId": "22222222-2222-4222-8222-222222222222",
                    "expectedRevision": "1",
                },
            ).status_code
            == 401
        )
        response = client.put("/api/drafts/11111111-1111-4111-8111-111111111111", json={})
        assert response.status_code == 426
        assert response.json()["error"] == "errors.clientUpgradeRequired"
        assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v2/drafts",
        "/api/v2/drafts/export.csv",
        "/api/v2/drafts/11111111-1111-4111-8111-111111111111/export.csv",
    ],
)
def test_draft_collection_and_csv_require_auth_and_are_private(path):
    app = create_app(Settings(_env_file=None, workflow_v2=True))
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "private, no-store"


def test_v2_rejects_client_supplied_analysis_even_with_valid_identifiers():
    from scope_guard_api.dependencies import current_owner

    app = create_app(Settings(_env_file=None, workflow_v2=True))
    app.dependency_overrides[current_owner] = lambda: {"id": "11111111-1111-4111-8111-111111111111"}
    with TestClient(app) as client:
        result = client.post(
            "/api/v2/drafts/11111111-1111-4111-8111-111111111111/analyses",
            json={
                "expectedRevision": "1",
                "operationId": "22222222-2222-4222-8222-222222222222",
                "locale": "en",
                "resultSnapshot": {"verdict": "in_scope"},
            },
        )
        assert result.status_code == 400


@pytest.mark.parametrize(
    ("code", "status"), [("analysisUnavailable", 503), ("analysisFailed", 502)]
)
def test_generation_errors_keep_their_workflow_status_and_code(code, status):
    from scope_guard.domain.analysis.domain import GenerationError

    app = create_app(Settings(_env_file=None, workflow_v2=True))

    @app.get("/_test/generation-error")
    async def generation_error():
        raise GenerationError(code, status)

    with TestClient(app) as client:
        response = client.get("/_test/generation-error")

    assert response.status_code == status
    assert response.json() == {"error": f"errors.{code}"}
    assert response.headers["cache-control"] == "private, no-store"
