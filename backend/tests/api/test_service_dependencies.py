from fastapi.testclient import TestClient
from scope_guard_api.dependencies import current_owner, extraction_service, health_service
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings


def test_ready_uses_overridable_service():
    class Ready:
        async def ready(self):
            return True

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[health_service] = Ready
    with TestClient(app) as client:
        assert client.get("/health/ready").json() == {"status": "ok", "database": "ok"}


def test_scope_route_calls_overridable_service():
    class Extract:
        async def extract(self, name, mime, data):
            assert (name, mime, data) == ("scope.txt", "text/plain", b"Hello")
            return b'{"text":"Service-owned","warnings":[]}'

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[current_owner] = lambda: {"id": "owner"}
    app.dependency_overrides[extraction_service] = Extract
    with TestClient(app) as client:
        result = client.post(
            "/api/scope/extract", files={"file": ("scope.txt", b"Hello", "text/plain")}
        )
        assert result.json() == {"text": "Service-owned", "warnings": []}
