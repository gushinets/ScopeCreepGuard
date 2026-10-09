import asyncio
import time

import httpx
import pytest
from fastapi import Request
from integration.support import replay_drizzle
from pydantic import SecretStr
from sqlalchemy import delete, func, select

from scope_guard.api.dependencies import auth_service
from scope_guard.core.config import Settings
from scope_guard.infrastructure.auth.passwords import Passwords
from scope_guard.infrastructure.database.models import UserRow
from scope_guard.main import create_app

pytestmark = pytest.mark.integration


def test_register_race_login_me_logout_deleted_user(disposable_url):
    replay_drizzle(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic-secret"),
            )
        )
        async with app.router.lifespan_context(app):
            barrier = asyncio.Barrier(2)

            class RacingPasswords(Passwords):
                async def hash(self, password):
                    # Both requests have completed the precheck before either can insert.
                    await barrier.wait()
                    return await super().hash(password)

            def service(request: Request):
                result = auth_service(request)
                result.passwords = RacingPasswords()
                return result

            app.dependency_overrides[auth_service] = service
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as c:
                body = {"email": " Owner@Example.Test ", "password": "synthetic-password"}
                responses = await asyncio.gather(
                    *[c.post("/api/auth/register", json=body) for _ in range(2)]
                )
                assert sorted(r.status_code for r in responses) == [201, 409]
                success = next(r for r in responses if r.status_code == 201)
                assert success.json()["user"]["email"] == "owner@example.test"
                assert next(r for r in responses if r.status_code == 409).json() == {
                    "error": "errors.duplicateEmail"
                }
                cookie = success.headers["set-cookie"]
                app.dependency_overrides.clear()
                for value in ("Max-Age=604800", "HttpOnly", "Path=/", "SameSite=lax"):
                    assert value in cookie
                async with app.state.database.new_uow() as uow:
                    assert await uow.session.scalar(select(func.count()).select_from(UserRow)) == 1
                    row = await uow.session.scalar(select(UserRow))
                    assert row.password_hash.startswith("$2b$12$")
                login = await c.post("/api/auth/login", json=body)
                assert login.status_code == 200 and login.json() == success.json()
                assert (await c.get("/api/auth/me")).json() == success.json()
                token = login.cookies["scg_session"]
                for invalid in ("malformed", token[:-8] + "tampered"):
                    bad = await c.get("/api/auth/me", headers={"cookie": "scg_session=" + invalid})
                    assert bad.status_code == 401
                    assert "Max-Age=0" in bad.headers["set-cookie"]
                app.state.clock = lambda: 9999999999
                expired = await c.get("/api/auth/me", headers={"cookie": "scg_session=" + token})
                assert expired.status_code == 401 and "Max-Age=0" in expired.headers["set-cookie"]
                app.state.clock = time.time
                c.cookies.set("scg_session", token)
                wrong = await c.post("/api/auth/login", json={**body, "password": "wrong-password"})
                assert wrong.status_code == 401 and wrong.json() == {
                    "error": "errors.invalidCredentials"
                }
                async with app.state.database.new_uow() as uow:
                    await uow.session.execute(delete(UserRow))
                    await uow.commit()
                deleted = await c.get("/api/auth/me")
                assert deleted.status_code == 401
                assert "Max-Age=0" in deleted.headers["set-cookie"]
                logout = await c.post("/api/auth/logout")
                assert logout.json() == {"ok": True} and "Max-Age=0" in logout.headers["set-cookie"]
                assert (await c.get("/api/auth/me")).status_code == 401

    asyncio.run(run())
