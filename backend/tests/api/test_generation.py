from fastapi.testclient import TestClient

from scope_guard.api.dependencies import current_owner
from scope_guard.core.config import Settings
from scope_guard.main import create_app

PATHS = (
    "/api/analyze",
    "/api/replies/regenerate",
    "/api/client-materials/language",
    "/api/change-orders/estimate",
)


def test_auth_and_input_errors_remain_envelopes():
    app = create_app(Settings(_env_file=None))
    client = TestClient(app)
    for path in PATHS:
        response = client.post(path, json={})
        assert response.status_code == 401
        assert response.json() == {"error": "errors.authRequired"}
    app.dependency_overrides[current_owner] = lambda: {"id": "11111111-1111-4111-8111-111111111111"}
    for path in PATHS:
        response = client.post(path, content="[")
        assert response.status_code == 400
        assert response.json() == {"error": "errors.requestBodyInvalid"}
        assert "cache-control" not in response.headers


def test_origin_precedes_auth_and_four_routes_in_openapi():
    app = create_app(Settings(_env_file=None, allowed_origins=("https://example.invalid",)))
    with TestClient(app) as client:
        for path in PATHS:
            assert path in app.openapi()["paths"]
            assert (
                client.post(
                    path, headers={"Origin": "https://foreign.invalid"}, json={}
                ).status_code
                == 403
            )
