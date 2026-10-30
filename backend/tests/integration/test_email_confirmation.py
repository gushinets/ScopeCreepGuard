import asyncio
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
import pytest
from integration.support import prepare_alembic
from pydantic import SecretStr
from scope_guard_api import bootstrap
from scope_guard_api.main import create_app
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.integrations.auth.passwords import Passwords
from scope_guard.services.auth.tokens import AuthTokenService
from scope_guard.services.email.contracts import EmailError
from scope_guard.services.email.service import EmailService

pytestmark = pytest.mark.integration


def test_pending_http_journey_and_duplicate_takeover(disposable_url, monkeypatch, caplog):
    prepare_alembic(disposable_url, target="head")
    messages = []

    class Sender:
        async def send(self, message):
            messages.append(message)

    monkeypatch.setattr(bootstrap, "email_service", lambda request: EmailService(Sender()))

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic"),
                workflow_v2=True,
                allowed_origins=("http://test",),
                public_app_url="http://localhost:3000",
            )
        )
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app)
            async with (
                httpx.AsyncClient(transport=transport, base_url="http://test") as owner,
                httpx.AsyncClient(transport=transport, base_url="http://test") as other,
            ):
                body = {
                    "email": " Owner@Example.Test ",
                    "password": "original-password",
                    "locale": "ru",
                }
                registered = await owner.post("/api/auth/register", json=body)
                assert registered.status_code == 201
                identity = registered.json()["user"]
                assert identity["workspaceAccess"] == "email_confirmation_required"
                assert registered.json()["emailConfirmation"]["status"] == "accepted"
                assert messages[0].locale == "ru"
                assert "session_version" not in str(registered.json())
                user_id = UUID(identity["id"])
                url = next(
                    line for line in messages[0].text.splitlines() if line.startswith("http")
                )
                fragment = parse_qs(urlsplit(url).fragment)
                token = fragment["token"][0]
                assert fragment["userId"] == [str(user_id)]
                for path in (
                    "/api/v2/projects",
                    "/api/v2/profile",
                    "/api/v2/drafts",
                    "/api/v2/history/00000000-0000-0000-0000-000000000001",
                    "/api/v2/exports/00000000-0000-0000-0000-000000000001/download",
                ):
                    response = await owner.get(path)
                    assert response.status_code == 403, (path, response.text)
                    assert response.json()["error"] == "errors.emailVerificationRequired"
                assert (await owner.get("/api/auth/me")).json()["user"] == identity
                limited = await owner.post("/api/auth/email/resend", json={"locale": "en"})
                assert limited.status_code == 429 and 1 <= int(limited.headers["Retry-After"]) <= 60
                assert (await other.get("/api/auth/me")).status_code == 401
                assert (await other.get("/api/auth/email/confirm")).status_code == 405
                for payload in (
                    {"userId": str(user_id), "token": "invalid" * 6},
                    {"userId": str(UUID(int=1)), "token": token},
                ):
                    assert (
                        await other.post("/api/auth/email/confirm", json=payload)
                    ).status_code == 400
                assert (
                    await other.post(
                        "/api/auth/email/confirm",
                        json={"userId": str(user_id), "token": token},
                        headers={"Origin": "https://evil.test"},
                    )
                ).status_code == 403
                service = AuthTokenService(
                    lambda: AuthUnitOfWork(app.state.database.new_uow()), Passwords()
                )
                assert await service.inspect(user_id, "verify_email", token)
                wrong = await service.issue(user_id, "reset_password")
                assert (
                    await other.post(
                        "/api/auth/email/confirm", json={"userId": str(user_id), "token": wrong.raw}
                    )
                ).status_code == 400
                for state in ("pending", "verified"):
                    duplicate = await other.post(
                        "/api/auth/register",
                        json={
                            **body,
                            "email": "OWNER@example.test",
                            "password": "attacker-password",
                        },
                    )
                    assert duplicate.status_code == 409 and "set-cookie" not in duplicate.headers
                    if state == "pending":
                        confirmed = await other.post(
                            "/api/auth/email/confirm", json={"userId": str(user_id), "token": token}
                        )
                        assert (
                            confirmed.status_code == 200
                            and "scg_session=" not in confirmed.headers.get("set-cookie", "")
                        )
                assert (await other.get("/api/auth/me")).status_code == 401
                assert (await owner.get("/api/auth/me")).json()["user"][
                    "workspaceAccess"
                ] == "allowed"
                assert (await owner.get("/api/v2/projects")).status_code == 200
                assert (
                    await owner.post(
                        "/api/auth/email/confirm", json={"userId": str(user_id), "token": token}
                    )
                ).status_code == 400
                assert (
                    await other.post(
                        "/api/auth/login", json={**body, "password": "attacker-password"}
                    )
                ).status_code == 401
                assert token not in caplog.text
                assert token not in str(registered.json())

    asyncio.run(run())


def test_source_and_hourly_account_limits(disposable_url, monkeypatch):
    import hashlib
    import hmac

    from scope_guard.database.repositories.email_confirmation import ConfirmationAttempts
    from scope_guard.services.auth.confirmation import ResendLimited

    prepare_alembic(disposable_url, target="head")

    class Sender:
        async def send(self, message):
            raise AssertionError("Source-limited registration must not send")

    monkeypatch.setattr(bootstrap, "email_service", lambda request: EmailService(Sender()))

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic"),
            )
        )
        async with app.router.lifespan_context(app):
            attempts = ConfirmationAttempts(app.state.database.new_uow)
            async with app.state.database.new_uow() as work:
                owners = (
                    (
                        await work.session.execute(
                            text("""
                    INSERT INTO users(email,password_hash)
                    SELECT 'source-'||n||'@example.test','unused-hash' FROM generate_series(1,35) n
                    RETURNING id
                """)
                        )
                    )
                    .scalars()
                    .all()
                )
                await work.commit()
            source = hmac.new(
                b"synthetic", b"email-confirmation-source:127.0.0.1", hashlib.sha256
            ).hexdigest()
            outcomes = await asyncio.gather(
                *[attempts.reserve(owner, source) for owner in owners], return_exceptions=True
            )
            assert sum(isinstance(r, ResendLimited) for r in outcomes) == 5
            assert sum(isinstance(r, UUID) for r in outcomes) == 30
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                registered = await client.post(
                    "/api/auth/register",
                    json={"email": "limited@example.test", "password": "original-password"},
                )
                assert registered.status_code == 201
                state = registered.json()["emailConfirmation"]
                assert state["status"] == "not_attempted" and state["retryAfter"] > 3500
                restored = (await client.get("/api/auth/me")).json()["emailConfirmation"]
                assert restored["status"] == "not_attempted" and restored["retryAfter"] > 3500
            # Five spaced attempts still consume the sliding account-hour quota.
            async with app.state.database.new_uow() as work:
                owner = await work.session.scalar(
                    text("SELECT id FROM users WHERE email='limited@example.test'")
                )
                await work.session.execute(
                    text("""
                    INSERT INTO email_confirmation_attempts(user_id,source_hash,created_at)
                    SELECT :owner,:source,clock_timestamp()-n*interval '70 seconds'
                    FROM generate_series(1,5) n
                """),
                    {"owner": owner, "source": "b" * 64},
                )
                await work.commit()
            with pytest.raises(ResendLimited) as blocked:
                await attempts.reserve(owner, "c" * 64)
            assert blocked.value.retry_after > 3200

    asyncio.run(run())


def test_atomic_resend_and_recoverable_delivery(disposable_url, monkeypatch):
    prepare_alembic(disposable_url, target="head")

    class Sender:
        async def send(self, message):
            raise EmailError("ambiguous")

    monkeypatch.setattr(bootstrap, "email_service", lambda request: EmailService(Sender()))

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic"),
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                registered = await client.post(
                    "/api/auth/register",
                    json={"email": "timeout@example.test", "password": "original-password"},
                )
                assert registered.status_code == 201
                assert registered.json()["emailConfirmation"]["status"] == "unknown"
                await client.post("/api/auth/logout")
                login = await client.post(
                    "/api/auth/login",
                    json={"email": "timeout@example.test", "password": "original-password"},
                )
                assert login.json()["user"]["workspaceAccess"] == "email_confirmation_required"
                async with app.state.database.new_uow() as work:
                    await work.session.execute(
                        text(
                            "UPDATE email_confirmation_attempts "
                            "SET created_at=created_at-interval '61 seconds'"
                        )
                    )
                    await work.commit()
                requests = await asyncio.gather(
                    *[
                        client.post("/api/auth/email/resend", json={"locale": "en"})
                        for _ in range(6)
                    ]
                )
                assert [r.status_code for r in requests].count(200) == 1
                assert [r.status_code for r in requests].count(429) == 5
                async with app.state.database.new_uow() as work:
                    assert await work.session.scalar(text("SELECT count(*) FROM auth_tokens")) == 2
                    assert (
                        await work.session.scalar(
                            text("SELECT count(*) FROM auth_tokens WHERE revoked_at IS NOT NULL")
                        )
                        == 0
                    )
                # Simulate process interruption after account commit but before any send.
                async with app.state.database.new_uow() as work:
                    await work.session.execute(
                        text(
                            "INSERT INTO users(email,password_hash) "
                            "VALUES ('interrupted@example.test',:hash)"
                        ),
                        {"hash": await Passwords().hash("original-password")},
                    )
                    await work.commit()
                result = await client.post(
                    "/api/auth/login",
                    json={"email": "interrupted@example.test", "password": "original-password"},
                )
                assert result.json()["emailConfirmation"] == {
                    "status": "not_attempted",
                    "retryAfter": 0,
                }

    asyncio.run(run())
