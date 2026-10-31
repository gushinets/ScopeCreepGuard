import asyncio
from uuid import uuid4

import pytest
from integration.support import prepare_alembic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


def test_public_http_known_unknown_normalization_and_reset(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        import httpx
        from pydantic import SecretStr
        from scope_guard_api.main import create_app

        from scope_guard.core.config import Settings
        from scope_guard.database.repositories.users import AuthUnitOfWork
        from scope_guard.integrations.auth.passwords import Passwords
        from scope_guard.services.auth.tokens import AuthTokenService

        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic"),
                public_app_url="http://localhost:3000",
                allowed_origins=("http://test",),
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                created = await client.post(
                    "/api/auth/register",
                    json={"email": "owner@example.test", "password": "old-password"},
                )
                assert created.status_code == 201
                owner = __import__("uuid").UUID(created.json()["user"]["id"])
                old_cookie = client.cookies.get("scg_session")
                known = await client.post(
                    "/api/auth/password/request",
                    json={"email": " Owner@Example.Test ", "locale": "ru"},
                )
                unknown = await client.post(
                    "/api/auth/password/request",
                    json={"email": "missing@example.test", "locale": "en"},
                )
                assert known.status_code == unknown.status_code == 202
                assert known.content == unknown.content == b'{"ok":true}'
                for index in range(8):
                    response = await client.post(
                        "/api/auth/password/request",
                        json={"email": f"spoof-{index}@example.test"},
                        headers={"X-Forwarded-For": f"192.0.2.{index}"},
                    )
                    assert response.status_code == 202
                blocked = await client.post(
                    "/api/auth/password/request",
                    json={"email": "another@example.test"},
                    headers={"X-Forwarded-For": "203.0.113.1"},
                )
                assert blocked.status_code == 429
                db = app.state.database
                tokens = AuthTokenService(lambda: AuthUnitOfWork(db.new_uow()), Passwords())
                token = await tokens.issue(owner, "reset_password")
                malformed = await client.post(
                    "/api/auth/password/reset",
                    content=(
                        '{"userId":"'
                        + str(owner)
                        + '","token":"abcdefghijklmnopqrst\\ud800","password":"new-password"}'
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )
                assert malformed.status_code == 400
                reset = await client.post(
                    "/api/auth/password/reset",
                    json={
                        "userId": str(owner),
                        "token": token.raw,
                        "password": "new-password",
                        "locale": "ru",
                    },
                )
                assert reset.status_code == 200
                assert "set-cookie" not in reset.headers
                assert (
                    await client.get(
                        "/api/auth/me", headers={"cookie": f"scg_session={old_cookie}"}
                    )
                ).status_code == 401
                assert (
                    await client.post(
                        "/api/auth/login",
                        json={"email": "owner@example.test", "password": "old-password"},
                    )
                ).status_code == 401
                assert (
                    await client.post(
                        "/api/auth/login",
                        json={"email": "owner@example.test", "password": "new-password"},
                    )
                ).json()["user"]["id"] == str(owner)
                assert (
                    await client.post(
                        "/api/auth/password/reset",
                        json={
                            "userId": str(owner),
                            "token": token.raw,
                            "password": "third-password",
                        },
                    )
                ).status_code == 400

    asyncio.run(run())


def test_capacity_cleanup_and_counter_cardinality(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.database.repositories.password_recovery import (
            RecoveryLimited,
            RecoveryQueue,
            RecoveryUnavailable,
        )

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        queue = RecoveryQueue(lambda: SqlAlchemyUnitOfWork(sessions), "test")
        try:
            async with sessions.begin() as db:
                await db.execute(
                    text("""INSERT INTO email_jobs(purpose,recipient,locale)
                    SELECT 'password_recovery','missing@example.test','en'
                    FROM generate_series(1,9999)""")
                )
            results = await asyncio.gather(
                queue.request("a@example.test", "en", "a"),
                queue.request("b@example.test", "en", "b"),
                return_exceptions=True,
            )
            assert sum(isinstance(result, RecoveryUnavailable) for result in results) == 1
            async with sessions.begin() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 10000
                await db.execute(
                    text(
                        "UPDATE email_jobs SET state='accepted',"
                        "updated_at=clock_timestamp()-interval '8 days'"
                    )
                )
                await db.execute(text("DELETE FROM recovery_limits"))
                await db.execute(
                    text("""INSERT INTO recovery_limits(id,window_started_at,count,expires_at)
                    SELECT 'synthetic-'||n,clock_timestamp(),1,clock_timestamp()-interval '25 hours'
                    FROM generate_series(1,50000) AS n""")
                )
            with pytest.raises(RecoveryLimited):
                await queue.request("c@example.test", "en", "c")
            await queue.cleanup()
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 9500
                assert await db.scalar(text("SELECT count(*) FROM recovery_limits")) == 49500
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_crash_after_preparation_replaces_token_and_fences_stale_worker(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from urllib.parse import parse_qs, urlsplit

        from scope_guard.database.repositories.password_recovery import RecoveryQueue
        from scope_guard.database.repositories.users import AuthUnitOfWork
        from scope_guard.integrations.auth.passwords import Passwords
        from scope_guard.services.auth.tokens import AuthTokenService
        from scope_guard.services.email.recovery_worker import RecoveryWorker

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        queue = RecoveryQueue(lambda: SqlAlchemyUnitOfWork(sessions), "test")
        tokens = AuthTokenService(
            lambda: AuthUnitOfWork(SqlAlchemyUnitOfWork(sessions)), Passwords()
        )
        worker = RecoveryWorker(queue, tokens, None, "http://localhost:3000")
        owner = uuid4()
        try:
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "INSERT INTO users(id,email,password_hash) "
                        "VALUES (:id,'owner@example.test','old')"
                    ),
                    {"id": owner},
                )
                await db.execute(
                    text("""INSERT INTO projects(user_id,name,industry,scope,updated_at)
                    VALUES (:id,'Preserved','Development','original scope',now())"""),
                    {"id": owner},
                )
                await db.execute(
                    text("""INSERT INTO drafts(project_id,draft_document,request_text,
                    analysis_is_stale,revision) SELECT id,'{}','preserved request',true,1
                    FROM projects WHERE user_id=:id"""),
                    {"id": owner},
                )
                await db.execute(
                    text("""INSERT INTO history_entries(project_id,date,request,verdict,
                    summary,check_snapshot,schema_version,source_kind) SELECT id,'2026-10-01',
                    'preserved','in_scope','original','{}',1,'legacy_unverified'
                    FROM projects WHERE user_id=:id"""),
                    {"id": owner},
                )
                before = {
                    table: (await db.execute(text(f"SELECT to_jsonb(t) FROM {table} t"))).all()
                    for table in ("projects", "drafts", "history_entries")
                }
            async with sessions.begin() as db:
                await db.execute(
                    text("""INSERT INTO email_jobs(purpose,recipient,locale,expires_at)
                    VALUES ('password_recovery','owner@example.test','en',
                    clock_timestamp()-interval '1 second')""")
                )
            expired = await queue.claim()
            assert await worker.prepare(expired) is None
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM auth_tokens")) == 0
            await queue.request("owner@example.test", "en", "source")
            first = await queue.claim()
            _, first_url = await worker.prepare(first)
            first_token = parse_qs(urlsplit(first_url).fragment)["token"][0]
            # Same recovery path whether death occurred before SMTP or after its acceptance.
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "UPDATE email_jobs SET "
                        "lease_expires_at=clock_timestamp()-interval '1 second'"
                    )
                )
            second = await queue.claim()
            assert await worker.prepare(first) is None
            _, second_url = await worker.prepare(second)
            second_token = parse_qs(urlsplit(second_url).fragment)["token"][0]
            assert not await tokens.inspect(owner, "reset_password", first_token)
            assert await tokens.inspect(owner, "reset_password", second_token)
            assert not await queue.finish(first["id"], first["lease_owner"], "accepted")
            assert await queue.finish(second["id"], second["lease_owner"], "accepted")
            await tokens.reset_password(owner, second_token, "data-preservation-password")
            async with sessions() as db:
                for table, expected in before.items():
                    assert (
                        await db.execute(text(f"SELECT to_jsonb(t) FROM {table} t"))
                    ).all() == expected
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_durable_admission_limits_and_fenced_claims(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.database.repositories.password_recovery import RecoveryQueue

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        queue = RecoveryQueue(lambda: SqlAlchemyUnitOfWork(sessions), "synthetic")
        try:
            await asyncio.gather(
                *[queue.request("nobody@example.test", "ru", "peer") for _ in range(8)]
            )
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 1
            first, second = await asyncio.gather(queue.claim(), queue.claim())
            job = first or second
            assert job and not (first and second)
            assert not await queue.finish(job["id"], uuid4(), "accepted")
            assert await queue.finish(job["id"], job["lease_owner"], "accepted")
            assert await queue.claim() is None
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_source_global_limits_and_restart_fencing(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.database.repositories.password_recovery import (
            RecoveryLimited,
            RecoveryQueue,
        )

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        queue = RecoveryQueue(lambda: SqlAlchemyUnitOfWork(sessions), "synthetic")
        try:
            for index in range(10):
                await queue.request(f"missing{index}@example.test", "en", "one-source")
            with pytest.raises(RecoveryLimited):
                await queue.request("missing11@example.test", "en", "one-source")
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 10
            old = await queue.claim()
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "UPDATE email_jobs SET "
                        "lease_expires_at=clock_timestamp()-interval '1 second' "
                        "WHERE id=:id"
                    ),
                    {"id": old["id"]},
                )
            fresh = await queue.claim()
            assert fresh["id"] == old["id"] and fresh["lease_owner"] != old["lease_owner"]
            assert not await queue.finish(old["id"], old["lease_owner"], "accepted")
            assert await queue.finish(fresh["id"], fresh["lease_owner"], "accepted")
            async with sessions.begin() as db:
                await db.execute(
                    text("UPDATE recovery_limits SET count=100 WHERE id='request:global-minute'")
                )
                before = await db.scalar(text("SELECT count(*) FROM recovery_limits"))
            with pytest.raises(RecoveryLimited):
                await queue.request("arbitrary@example.test", "en", "new-source")
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM recovery_limits")) == before
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "UPDATE email_jobs SET state='leased',attempts=5,"
                        "lease_expires_at=clock_timestamp()-interval '1 second' "
                        "WHERE state='pending'"
                    )
                )
                await db.execute(
                    text("""INSERT INTO email_jobs
                    (purpose,recipient,locale,state,attempts,lease_expires_at)
                    SELECT 'password_recovery','missing@example.test','en','leased',5,
                    clock_timestamp()-interval '1 second' FROM generate_series(1,501)""")
                )
            assert await queue.claim() is None
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "category,retries",
    [("temporary", True), ("ambiguous", True), ("rejected", False), ("invalid", False)],
)
def test_delivery_failure_and_retry_bound(disposable_url, category, retries):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from scope_guard.database.repositories.password_recovery import RecoveryQueue
        from scope_guard.database.repositories.users import AuthUnitOfWork
        from scope_guard.integrations.auth.passwords import Passwords
        from scope_guard.services.auth.tokens import AuthTokenService
        from scope_guard.services.email.contracts import EmailError
        from scope_guard.services.email.recovery_worker import RecoveryWorker
        from scope_guard.services.email.service import EmailService

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)

        def factory():
            return SqlAlchemyUnitOfWork(sessions)

        queue = RecoveryQueue(factory, "test")
        sent = []

        class Sender:
            async def send(self, message):
                # A separate transaction proves worker holds no user lock during SMTP.
                async with sessions.begin() as db:
                    await db.execute(text("SET LOCAL lock_timeout='100ms'"))
                    await db.execute(text("SELECT id FROM users FOR UPDATE"))
                sent.append(message)
                raise EmailError(category)

        tokens = AuthTokenService(lambda: AuthUnitOfWork(factory()), Passwords())
        worker = RecoveryWorker(queue, tokens, EmailService(Sender()), "http://localhost:3000")
        try:
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "INSERT INTO users(email,password_hash) VALUES ('owner@example.test','old')"
                    )
                )
            await queue.request("owner@example.test", "en", "source")
            await worker.once()
            async with sessions() as db:
                row = (await db.execute(text("SELECT * FROM email_jobs"))).mappings().one()
                assert row["state"] == ("pending" if retries else "failed")
                assert row["failure_category"] == category
                if retries:
                    assert (row["next_attempt_at"] - row["updated_at"]).total_seconds() >= 59
            if retries:
                for _ in range(4):
                    async with sessions.begin() as db:
                        await db.execute(
                            text("UPDATE email_jobs SET next_attempt_at=clock_timestamp()")
                        )
                    await worker.once()
                async with sessions() as db:
                    assert await db.scalar(text("SELECT state FROM email_jobs")) == "failed"
                    assert (
                        await db.scalar(
                            text("SELECT count(*) FROM auth_tokens WHERE revoked_at IS NULL")
                        )
                        == 1
                    )
                assert len(sent) == 5
                assert not await worker.once()
            else:
                assert len(sent) == 1
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_notification_enqueue_failure_rolls_back_reset(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from sqlalchemy.exc import DBAPIError

        from scope_guard.database.repositories.users import AuthUnitOfWork
        from scope_guard.integrations.auth.passwords import Passwords
        from scope_guard.services.auth.tokens import AuthTokenService

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        service = AuthTokenService(
            lambda: AuthUnitOfWork(SqlAlchemyUnitOfWork(sessions)), Passwords()
        )
        owner = uuid4()
        try:
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "INSERT INTO users(id,email,password_hash) "
                        "VALUES (:id,'owner@example.test','old')"
                    ),
                    {"id": owner},
                )
                await db.execute(
                    text("""CREATE FUNCTION fail_notification() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic enqueue failure'; END $$""")
                )
                await db.execute(
                    text(
                        "CREATE TRIGGER fail_notification BEFORE INSERT ON email_jobs "
                        "FOR EACH ROW EXECUTE FUNCTION fail_notification()"
                    )
                )
            token = await service.issue(owner, "reset_password")
            with pytest.raises(DBAPIError):
                await service.reset_password(owner, token.raw, "new-password")
            assert await service.inspect(owner, "reset_password", token.raw)
            async with sessions() as db:
                row = (
                    await db.execute(
                        text("SELECT password_hash,session_version,password_changed_at FROM users")
                    )
                ).one()
                assert tuple(row) == ("old", 0, None)
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 0
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize("notification_fails", [False, True])
def test_worker_delivery_reset_notification_and_obsolete_job(disposable_url, notification_fails):
    prepare_alembic(disposable_url, target="head")

    async def run():
        from urllib.parse import parse_qs, urlsplit

        from scope_guard.database.repositories.password_recovery import RecoveryQueue
        from scope_guard.database.repositories.users import AuthUnitOfWork
        from scope_guard.integrations.auth.passwords import Passwords
        from scope_guard.services.auth.tokens import AuthTokenService
        from scope_guard.services.email.recovery_worker import RecoveryWorker
        from scope_guard.services.email.service import EmailService

        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)

        def factory():
            return SqlAlchemyUnitOfWork(sessions)

        queue = RecoveryQueue(factory, "synthetic")
        tokens = AuthTokenService(lambda: AuthUnitOfWork(factory()), Passwords())
        messages = []

        class Sender:
            async def send(self, message):
                messages.append(message)
                if notification_fails and message.kind == "password_changed":
                    from scope_guard.services.email.contracts import EmailError

                    raise EmailError("rejected")

        worker = RecoveryWorker(queue, tokens, EmailService(Sender()), "http://localhost:3000")
        owner = uuid4()
        try:
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "INSERT INTO users(id,email,password_hash) "
                        "VALUES (:id,'owner@example.test','old')"
                    ),
                    {"id": owner},
                )
            await queue.request("unknown@example.test", "en", "a")
            await worker.once()
            assert not messages
            await queue.request("owner@example.test", "ru", "b")
            await worker.once()
            assert len(messages) == 1 and messages[0].locale == "ru"
            link = next(line for line in messages[0].text.splitlines() if line.startswith("http"))
            fragment = parse_qs(urlsplit(link).fragment)
            raw = fragment["token"][0]
            # Queue a pre-reset job that must not mint a post-reset link.
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "INSERT INTO email_jobs(purpose,recipient,locale) "
                        "VALUES ('password_recovery','owner@example.test','en')"
                    )
                )
            await tokens.reset_password(owner, raw, "new-password", locale="ru")
            await worker.once()
            assert len(messages) == 1
            await worker.once()
            assert len(messages) == 2 and messages[-1].kind == "password_changed"
            async with sessions() as db:
                row = (
                    (await db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": owner}))
                    .mappings()
                    .one()
                )
                assert row["session_version"] == 1
                assert row["email_verified_at"] is None
                assert await Passwords().verify("new-password", row["password_hash"])
                assert not await Passwords().verify("old", row["password_hash"])
            assert not await tokens.inspect(owner, "reset_password", raw)
        finally:
            await engine.dispose()

    asyncio.run(run())
