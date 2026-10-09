import asyncio

import httpx


def test_missing_or_unreachable_database_returns_sanitized_503():
    from scope_guard.core.config import Settings
    from scope_guard.main import create_app

    async def exercise(url):
        app = create_app(Settings(_env_file=None, database_url=url))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/health/ready")
                assert response.status_code == 503
                assert response.json() == {"status": "unavailable", "database": "unavailable"}
                assert response.headers["cache-control"] == "no-store"
                assert (await client.get("/health/live")).json() == {"status": "ok"}

    asyncio.run(exercise(None))
    asyncio.run(exercise("postgres://owner:do-not-leak@127.0.0.1:1/test"))
