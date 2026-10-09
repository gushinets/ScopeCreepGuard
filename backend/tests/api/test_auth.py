import asyncio

import httpx
import pytest
from pydantic import SecretStr

from scope_guard.core.config import Settings
from scope_guard.main import create_app


@pytest.mark.parametrize(
    "body,code",
    [
        (None, "requestBodyInvalid"),
        ([], "requestBodyInvalid"),
        ({}, "emailRequired"),
        ({"email": "bad"}, "passwordRequired"),
        ({"email": "bad", "password": "x"}, "invalidEmail"),
        ({"email": "a@b.test", "password": "x"}, "passwordTooShort"),
    ],
)
def test_auth_validation_precedes_database_access(body, code):
    async def run():
        app = create_app(Settings(_env_file=None, database_url=None))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as c:
            for path in ("register", "login"):
                response = await c.post("/api/auth/" + path, json=body)
                assert response.status_code == 400
                assert response.json() == {"error": "errors." + code}

    asyncio.run(run())


def test_logout_without_configuration_expires_cookie_and_me_requires_auth():
    async def run():
        app = create_app(Settings(_env_file=None, database_url=None))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as c:
            response = await c.post("/api/auth/logout")
            assert response.status_code == 200
            assert response.json() == {"ok": True}
            cookie = response.headers["set-cookie"]
            for part in ("scg_session=", "Max-Age=0", "HttpOnly", "SameSite=lax", "Path=/"):
                assert part in cookie
            assert (await c.get("/api/auth/me")).status_code == 401

    asyncio.run(run())


@pytest.mark.parametrize("path", ["register", "login", "logout"])
def test_auth_rejects_foreign_origins_before_parsing(path):
    async def run():
        app = create_app(Settings(_env_file=None, allowed_origins=("https://app.test",)))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as c:
            response = await c.post("/api/auth/" + path, content="{", headers={"origin": "null"})
            assert response.status_code == 403
            assert response.json() == {"error": "errors.requestFailed"}

    asyncio.run(run())


def test_production_logout_cookie_secure():
    async def run():
        app = create_app(
            Settings(_env_file=None, production=True, auth_secret=SecretStr("synthetic"))
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://test"
        ) as c:
            assert "Secure" in (await c.post("/api/auth/logout")).headers["set-cookie"]

    asyncio.run(run())


@pytest.mark.parametrize("secret", [None, SecretStr("")])
def test_unconfigured_auth_returns_sanitized_failure_without_cookie(secret):
    async def run():
        app = create_app(Settings(_env_file=None, database_url=None, auth_secret=secret))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            for path in ("register", "login"):
                response = await client.post(
                    "/api/auth/" + path, json={"email": "a@b.test", "password": "12345678"}
                )
                assert response.status_code == 500
                assert response.json() == {"error": "errors.requestFailed"}
                assert "set-cookie" not in response.headers

    asyncio.run(run())
