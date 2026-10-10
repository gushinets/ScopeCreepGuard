import asyncio

import httpx
import pytest

from scope_guard.core.config import Settings
from scope_guard.main import create_app


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/projects"),
        ("POST", "/api/projects"),
        ("GET", "/api/projects/bad-id"),
        ("PATCH", "/api/projects/bad-id"),
        ("DELETE", "/api/projects/bad-id"),
    ],
)
def test_project_auth_precedes_body_and_identifier(method, path):
    async def run():
        app = create_app(Settings(_env_file=None, database_url=None, auth_secret=None))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.request(method, path, content="{")
            assert response.status_code == 401
            assert response.json() == {"error": "errors.authRequired"}
            assert "set-cookie" not in response.headers

    asyncio.run(run())


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/projects"),
        ("PATCH", "/api/projects/bad-id"),
        ("DELETE", "/api/projects/bad-id"),
    ],
)
def test_project_origin_precedes_auth(method, path):
    async def run():
        app = create_app(Settings(_env_file=None, allowed_origins=("https://app.test",)))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://app.test"
        ) as client:
            response = await client.request(
                method, path, content="{", headers={"origin": "https://foreign.test"}
            )
            assert response.status_code == 403
            assert response.json() == {"error": "errors.requestFailed"}

    asyncio.run(run())
