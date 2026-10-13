"""Admission/polling contract and legacy restrictions on owned disposable PostgreSQL."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from scope_guard_api.dependencies import current_owner
from scope_guard_api.main import create_app
from sqlalchemy import create_engine, text

from scope_guard.core.config import Settings
from scope_guard.database.migrations import migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration


def test_admission_status_is_read_only_and_legacy_requires_stable_owned_context(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('api-llm@example.test','hash') RETURNING id"
            )
        )
    app = create_app(
        Settings(
            _env_file=None,
            database_url=disposable_url,
            auth_secret="disposable-secret-at-least-32-characters",
            openai_api_key="synthetic",
            openai_model="gpt-5.4-nano",
            workflow_v2=True,
            llm_workflow=True,
            llm_input_rate_bound=".000001",
            llm_output_rate_bound=".000002",
        )
    )
    app.dependency_overrides[current_owner] = lambda: {"id": str(owner)}
    with TestClient(app) as client:
        project = client.post(
            "/api/v2/projects",
            json={
                "operationId": str(uuid4()),
                "name": "API",
                "industry": "Development",
                "scope": "Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
                "hourlyRate": "30.00",
                "fixedPrice": None,
            },
        ).json()["project"]
        draft = client.get(f"/api/v2/projects/{project['id']}/draft").json()["draft"]
        draft = client.put(
            f"/api/v2/drafts/{draft['id']}",
            json={
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"requestText": "Please add Arrow and email alerts."},
            },
        ).json()["draft"]
        command = {
            "operationId": str(uuid4()),
            "expectedRevision": draft["revision"],
            "locale": "ru",
        }
        url = f"/api/v2/drafts/{draft['id']}/analyses"
        admitted = client.post(url, json=command)
        assert admitted.status_code == 202, admitted.text
        assert (
            client.post(url, json=command).json()["operationId"] == admitted.json()["operationId"]
        )
        assert admitted.headers["idempotency-key"] == command["operationId"]
        for _ in range(2):
            status = client.get(admitted.headers["location"])
            assert status.status_code == 200 and status.json()["status"] == "queued"
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM provider_calls")) == 0
            assert connection.scalar(text("SELECT max(epoch) FROM llm_operations")) == 0
        # All four legacy generation endpoints share the same admission path.
        legacy = {
            "draftId": draft["id"],
            "expectedRevision": draft["revision"],
            "projectId": project["id"],
            "request": draft["requestText"],
            "locale": "ru",
        }
        for path in (
            "/api/analyze",
            "/api/replies/regenerate",
            "/api/client-materials/language",
            "/api/change-orders/estimate",
        ):
            assert client.post(path, json=legacy).status_code == 428
            assert (
                client.post(
                    path,
                    json={**legacy, "operationId": str(uuid4())},
                    headers={"Idempotency-Key": str(uuid4())},
                ).status_code
                == 400
            )
        retry_key = str(uuid4())
        accepted = client.post("/api/analyze", json=legacy, headers={"Idempotency-Key": retry_key})
        assert accepted.status_code == 202, accepted.text
        assert (
            client.post("/api/analyze", json=legacy, headers={"Idempotency-Key": retry_key}).json()
            == accepted.json()
        )
        assert (
            client.post(
                "/api/analyze",
                json={**legacy, "request": "Tampered request."},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 409
        )
        app.state.settings.openai_model = "unknown-provider-tariff"
        app.state.settings.llm_input_rate_bound = None
        app.state.settings.llm_output_rate_bound = None
        refused_command = {**command, "operationId": str(uuid4())}
        refused = client.post(url, json=refused_command)
        assert (
            refused.status_code == 503
            and refused.json()["error"] == "errors.providerBudgetUnavailable"
        )
        assert client.post(url, json=refused_command).json() == refused.json()
        assert client.get(refused.headers["location"]).json()["status"] == "failed"
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM provider_calls")) == 0
        app.dependency_overrides[current_owner] = lambda: {"id": str(UUID(int=42))}
        assert client.get(admitted.headers["location"]).status_code == 404
        assert (
            client.post(
                "/api/analyze", json=legacy, headers={"Idempotency-Key": str(uuid4())}
            ).status_code
            == 404
        )
    engine.dispose()
