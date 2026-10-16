from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from scope_guard_api.dependencies import current_owner
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings
from scope_guard.domain.drafts.workflow import WorkflowError


@pytest.mark.parametrize("persistent", [False, True])
def test_disabled_durable_generation_never_returns_an_unsaved_success(persistent):
    app = create_app(Settings(_env_file=None, workflow_v2=persistent))
    app.dependency_overrides[current_owner] = lambda: {"id": str(uuid4())}
    with TestClient(app) as client:
        for path in (
            "/api/analyze",
            "/api/replies/regenerate",
            "/api/client-materials/language",
            "/api/change-orders/estimate",
        ):
            response = client.post(path, json={"request": "Add email alerts"})
            # V2 already retires unkeyed legacy callers; compatible mode now retires generation too.
            assert response.status_code == (426 if persistent else 503)
            assert response.json()["error"] in (
                "errors.workflowUnavailable",
                "errors.clientUpgradeRequired",
            )
        if persistent:
            for action in ("analyses", "estimate", "regenerate", "translate"):
                body = {"operationId": str(uuid4()), "expectedRevision": "1"}
                if action == "analyses":
                    body["locale"] = "en"
                if action == "translate":
                    body["language"] = "en"
                response = client.post(f"/api/v2/drafts/{uuid4()}/{action}", json=body)
                assert response.status_code == 503, response.text
                assert response.json() == {"error": "errors.workflowUnavailable"}


def test_document_error_fields_are_returned_without_losing_the_error_contract():
    app = create_app(Settings(_env_file=None))

    @app.get("/_test/readiness-error")
    async def fail():
        raise WorkflowError(
            "documentInvalid", fields={"description": "required", "additionalCost": "positive"}
        )

    with TestClient(app) as client:
        response = client.get("/_test/readiness-error")
        assert response.status_code == 400
        assert response.json() == {
            "error": "errors.documentInvalid",
            "fields": {"description": "required", "additionalCost": "positive"},
        }
