import asyncio

import httpx
import pytest


@pytest.mark.parametrize("integration_value", [None, "unavailable"])
def test_liveness_requires_no_integrations(monkeypatch, integration_value):
    for name in ("DATABASE_URL", "OPENAI_API_KEY", "AUTH_SECRET"):
        if integration_value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, integration_value)

    from scope_guard.main import create_app

    async def request_health():
        application = create_app()
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application), base_url="http://test"
            ) as client:
                return await client.get("/health/live")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


def test_openapi_describes_the_liveness_response():
    from scope_guard.main import create_app

    schema = create_app().openapi()
    response = schema["paths"]["/health/live"]["get"]["responses"]["200"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LivenessResponse"
    }
    assert list(schema["paths"]) == ["/health/live", "/health/ready"]
