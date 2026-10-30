import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from integration.support import prepare_alembic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.domain.auth.tokens import InvalidAuthToken
from scope_guard.integrations.auth.passwords import Passwords
from scope_guard.services.auth.tokens import AuthTokenService

pytestmark = pytest.mark.integration


def test_token_transactions(disposable_url, caplog):
    prepare_alembic(disposable_url, target="head")
    from sqlalchemy import create_engine

    from scope_guard.database.schema_verification import verify_nonblocking_schema

    probe = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    with probe.begin() as db:
        verify_nonblocking_schema(db)
    probe.dispose()

    async def run():
        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)

        def factory():
            return AuthUnitOfWork(SqlAlchemyUnitOfWork(sessions))

        passwords = Passwords()
        now = datetime(2026, 10, 30, tzinfo=UTC)
        service = AuthTokenService(factory, passwords, lambda: now)
        user_id = uuid4()
        async with sessions.begin() as db:
            await db.execute(
                text("INSERT INTO users(id,email,password_hash) VALUES (:id,'a@b.test',:p)"),
                {"id": user_id, "p": await passwords.hash("original-password")},
            )
        try:
            for purpose in ("verify_email", "reset_password"):
                token = await service.issue(user_id, purpose)
                assert token.expires_at == now + timedelta(hours=24)
                assert token.raw not in repr(token)
                async with sessions() as db:
                    row = (
                        (
                            await db.execute(
                                text("SELECT * FROM auth_tokens WHERE purpose=:p"), {"p": purpose}
                            )
                        )
                        .mappings()
                        .one()
                    )
                    assert row["token_hash"] == hashlib.sha256(token.raw.encode()).hexdigest()
                    assert token.raw not in str(dict(row))
                assert await service.inspect(user_id, purpose, token.raw)
                assert not await service.inspect(uuid4(), purpose, token.raw)
                other = "reset_password" if purpose == "verify_email" else "verify_email"
                assert not await service.inspect(user_id, other, token.raw)
                now += timedelta(hours=24)
                assert not await service.inspect(user_id, purpose, token.raw)
                now -= timedelta(hours=24)
                await service.revoke(user_id, purpose)
                assert not await service.inspect(user_id, purpose, token.raw)
            confirmations = [await service.issue(user_id, "verify_email") for _ in range(2)]
            await service.confirm_email(user_id, confirmations[0].raw)
            for token in confirmations:
                assert not await service.inspect(user_id, "verify_email", token.raw)
            async with sessions() as db:
                assert await db.scalar(text("SELECT email_verified_at FROM users")) == now
            resets = [await service.issue(user_id, "reset_password") for _ in range(2)]
            results = await asyncio.gather(
                *[service.reset_password(user_id, t.raw, "replacement-password") for t in resets],
                return_exceptions=True,
            )
            assert sum(r is None for r in results) == 1
            assert sum(isinstance(r, InvalidAuthToken) for r in results) == 1
            async with sessions() as db:
                row = (await db.execute(text("SELECT * FROM users"))).mappings().one()
                assert row["session_version"] == 1
                assert row["email_verified_at"] == now
                assert await passwords.verify("replacement-password", row["password_hash"])
            for token in resets:
                assert not await service.inspect(user_id, "reset_password", token.raw)
            same = await service.issue(user_id, "verify_email")
            results = await asyncio.gather(
                *[service.confirm_email(user_id, same.raw) for _ in range(2)],
                return_exceptions=True,
            )
            assert sum(r is None for r in results) == 1
            assert sum(isinstance(r, InvalidAuthToken) for r in results) == 1
            # Failure after mutation must roll back user and token together.
            token = await service.issue(user_id, "reset_password")
            from scope_guard.database.repositories.auth_tokens import AuthTokens

            original = AuthTokens.apply

            async def fail(self, *args):
                await original(self, *args)
                raise RuntimeError("synthetic failure")

            AuthTokens.apply = fail
            try:
                with pytest.raises(RuntimeError, match="synthetic failure"):
                    await service.reset_password(user_id, token.raw, "rolled-back-password")
            finally:
                AuthTokens.apply = original
            assert await service.inspect(user_id, "reset_password", token.raw)
            async with sessions() as db:
                assert await db.scalar(text("SELECT session_version FROM users")) == 1
                assert await passwords.verify(
                    "replacement-password", await db.scalar(text("SELECT password_hash FROM users"))
                )
            expiring = await service.issue(user_id, "reset_password")

            class ExpiringPasswords(Passwords):
                async def hash(self, password):
                    nonlocal now
                    now = expiring.expires_at
                    return await super().hash(password)

            service.passwords = ExpiringPasswords()
            with pytest.raises(InvalidAuthToken):
                await service.reset_password(user_id, expiring.raw, "too-late-password")
            async with sessions() as db:
                row = (await db.execute(text("SELECT * FROM users"))).mappings().one()
                assert row["session_version"] == 1
                assert await passwords.verify("replacement-password", row["password_hash"])
                assert (
                    await db.scalar(
                        text("SELECT used_at FROM auth_tokens WHERE token_hash=:h"),
                        {"h": hashlib.sha256(expiring.raw.encode()).hexdigest()},
                    )
                    is None
                )
            for secret in [
                expiring.raw,
                token.raw,
                same.raw,
                *(t.raw for t in resets),
                "replacement-password",
                "rolled-back-password",
                "too-late-password",
            ]:
                assert secret not in caplog.text
            assert "invalid_auth_token" == str(InvalidAuthToken())
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize("verified", [False, True])
def test_repeat_registration_never_takes_over(disposable_url, verified):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.domain.auth.validation import AuthError
        from scope_guard.integrations.auth.sessions import Sessions
        from scope_guard.services.auth.use_cases import AuthService

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)

        def factory():
            return AuthUnitOfWork(SqlAlchemyUnitOfWork(sessions))

        passwords = Passwords()
        codec = Sessions("synthetic")
        service = AuthService(factory, passwords, codec)
        original, session = await service.register(
            {"email": "owner@example.test", "password": "password-A"}
        )
        if verified:
            async with sessions.begin() as db:
                await db.execute(text("UPDATE users SET email_verified_at=now()"))
        tokens = AuthTokenService(factory, passwords)
        pending = await tokens.issue(__import__("uuid").UUID(original["id"]), "reset_password")
        await tokens.revoke(__import__("uuid").UUID(original["id"]), "reset_password")
        assert not await tokens.inspect(
            __import__("uuid").UUID(original["id"]), "reset_password", pending.raw
        )
        async with sessions() as db:
            token_state = (await db.execute(text("SELECT * FROM auth_tokens"))).mappings().all()
            before = (await db.execute(text("SELECT * FROM users"))).mappings().one()
        for email in ("owner@example.test", " Owner@Example.Test "):
            with pytest.raises(AuthError) as error:
                await service.register({"email": email, "password": "password-B"})
            assert error.value.status == 409
        async with sessions() as db:
            after = (await db.execute(text("SELECT * FROM users"))).mappings().one()
            assert dict(before) == dict(after)
            assert (
                await db.execute(text("SELECT * FROM auth_tokens"))
            ).mappings().all() == token_state
            assert after["email_verification_required"] is True
            assert await passwords.verify("password-A", after["password_hash"])
            assert not await passwords.verify("password-B", after["password_hash"])
        assert await service.me(session) == {
            **original,
            "workspaceAccess": "allowed" if verified else "email_confirmation_required",
        }
        async with sessions.begin() as db:
            await db.execute(text("UPDATE users SET session_version=1"))
        with pytest.raises(AuthError):
            await service.me(session)
        await engine.dispose()

    asyncio.run(run())


def test_upgrade_preserves_legacy_owned_data(disposable_url):
    from sqlalchemy import create_engine

    from scope_guard.database.migrations import migrate

    prepare_alembic(disposable_url, target="0008_contextual_onboarding")
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    with engine.begin() as db:
        owner = db.scalar(
            text(
                "INSERT INTO users(email,password_hash) "
                "VALUES ('legacy@b.test','preserve-hash') RETURNING id"
            )
        )
        db.execute(text("INSERT INTO profiles(user_id) VALUES (:id)"), {"id": owner})
        db.execute(
            text(
                "INSERT INTO projects(user_id,name,industry,scope,updated_at) "
                "VALUES (:id,'Legacy','Development','preserve scope',now())"
            ),
            {"id": owner},
        )
        before = {
            table: db.execute(text(f"SELECT row_to_json(t) FROM {table} t")).scalars().all()
            for table in ("users", "profiles", "projects")
        }
    with engine.begin() as db:
        migrate(db, target="head")
    with engine.begin() as db:
        for table in ("profiles", "projects"):
            assert (
                db.execute(text(f"SELECT row_to_json(t) FROM {table} t")).scalars().all()
                == before[table]
            )
        user = db.execute(text("SELECT * FROM users")).mappings().one()
        assert all(
            user[k] == v for k, v in before["users"][0].items() if k not in ("id", "created_at")
        )
        assert str(user["id"]) == before["users"][0]["id"]
        assert user["email_verified_at"] is None
        assert user["email_verification_required"] is False
        assert user["session_version"] == 0
    engine.dispose()


def test_issuance_reset_ordering(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.database.repositories.auth_tokens import AuthTokens

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)

        def factory():
            return AuthUnitOfWork(SqlAlchemyUnitOfWork(sessions))

        service = AuthTokenService(factory, Passwords())
        owner = uuid4()
        async with sessions.begin() as db:
            await db.execute(
                text("INSERT INTO users(id,email,password_hash) VALUES (:id,'race@b.test','old')"),
                {"id": owner},
            )
        initial = await service.issue(owner, "reset_password")
        # Hold issuance after acquiring the user lock; reset must wait behind it.
        acquired, release = asyncio.Event(), asyncio.Event()
        original = AuthTokens.insert

        async def paused(self, *args):
            acquired.set()
            await release.wait()
            await original(self, *args)

        AuthTokens.insert = paused
        try:
            issuance = asyncio.create_task(service.issue(owner, "reset_password"))
            await acquired.wait()
            reset = asyncio.create_task(service.reset_password(owner, initial.raw, "new-password"))
            release.set()
            issued, _ = await asyncio.gather(issuance, reset)
        finally:
            AuthTokens.insert = original
        assert not await service.inspect(owner, "reset_password", issued.raw)
        fresh = await service.issue(owner, "reset_password")
        assert await service.inspect(owner, "reset_password", fresh.raw)
        acquired, release, waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_apply, original_lock = AuthTokens.apply, AuthTokens.lock_user

        async def paused_reset(self, *args):
            acquired.set()
            await release.wait()
            await original_apply(self, *args)

        async def tracked_lock(self, user_id):
            if asyncio.current_task().get_name() == "waiting-issuance":
                waiting.set()
            await original_lock(self, user_id)

        AuthTokens.apply, AuthTokens.lock_user = paused_reset, tracked_lock
        try:
            reset = asyncio.create_task(service.reset_password(owner, fresh.raw, "next-password"))
            await acquired.wait()
            issuance = asyncio.create_task(
                service.issue(owner, "reset_password"), name="waiting-issuance"
            )
            await waiting.wait()
            release.set()
            _, after_reset = await asyncio.gather(reset, issuance)
        finally:
            AuthTokens.apply, AuthTokens.lock_user = original_apply, original_lock
        assert await service.inspect(owner, "reset_password", after_reset.raw)
        results = await asyncio.gather(
            *[service.reset_password(owner, after_reset.raw, "last-password") for _ in range(2)],
            return_exceptions=True,
        )
        assert sum(r is None for r in results) == 1
        assert sum(isinstance(r, InvalidAuthToken) for r in results) == 1

        with pytest.raises(InvalidAuthToken):
            await service.issue(uuid4(), "reset_password")
        await engine.dispose()

    asyncio.run(run())


def test_revocation_on_protected_routes(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        import base64
        import hmac
        import json

        import httpx
        from pydantic import SecretStr
        from scope_guard_api.main import create_app

        from scope_guard.core.config import Settings
        from scope_guard.integrations.auth.sessions import encode

        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic"),
                workflow_v2=True,
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                registered = await client.post(
                    "/api/auth/register",
                    json={"email": "routes@b.test", "password": "original-password"},
                )
                assert registered.status_code == 201
                confirmer = AuthTokenService(
                    lambda: AuthUnitOfWork(app.state.database.new_uow()), Passwords()
                )
                registered_owner = __import__("uuid").UUID(registered.json()["user"]["id"])
                confirmation = await confirmer.issue(registered_owner, "verify_email")
                await confirmer.confirm_email(registered_owner, confirmation.raw)
                session = registered.cookies["scg_session"]
                header, payload, _ = session.split(".")
                claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
                assert claims.pop("session_version") == 0
                unsigned = header + "." + encode(json.dumps(claims).encode())
                legacy = (
                    unsigned + "." + encode(hmac.digest(b"synthetic", unsigned.encode(), "sha256"))
                )
                routes = ("/api/auth/me", "/api/v2/projects", "/api/v2/profile")
                for token in (session, legacy):
                    for route in routes:
                        response = await client.get(
                            route, headers={"cookie": "scg_session=" + token}
                        )
                        assert response.status_code == 200, (route, response.text)
                service = AuthTokenService(
                    lambda: AuthUnitOfWork(app.state.database.new_uow()), Passwords()
                )
                owner = __import__("uuid").UUID(registered.json()["user"]["id"])
                token = await service.issue(owner, "reset_password")
                await service.reset_password(owner, token.raw, "replacement-password")
                for old in (session, legacy):
                    for route in routes:
                        response = await client.get(route, headers={"cookie": "scg_session=" + old})
                        assert response.status_code == 401
                login = await client.post(
                    "/api/auth/login",
                    json={"email": "routes@b.test", "password": "replacement-password"},
                )
                assert login.status_code == 200
                assert (await client.get("/api/v2/projects")).status_code == 200

    asyncio.run(run())
