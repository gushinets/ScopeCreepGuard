import asyncio

import httpx
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings


def test_public_recovery_is_bounded_and_fails_honestly_without_database():
    async def run():
        app = create_app(Settings(_env_file=None))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            oversized = await client.post("/api/auth/password/request", content=b"x" * 8193)
            assert oversized.status_code == 400
            malformed = await client.post(
                "/api/auth/password/request",
                content=b'{"email":"a\\ud800@example.test"}',
                headers={"Content-Type": "application/json"},
            )
            assert malformed.status_code == 400
            unavailable = await client.post(
                "/api/auth/password/request", json={"email": "a@example.test", "locale": "en"}
            )
            assert unavailable.status_code == 503
            assert unavailable.json() == {"error": "errors.requestFailed"}
            assert unavailable.headers["cache-control"] == "no-store"

    asyncio.run(run())
