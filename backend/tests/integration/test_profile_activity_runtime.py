"""Runtime facts are verified independently on an owned disposable database."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.users import Users
from scope_guard.database.session import Database, normalize_url

pytestmark = pytest.mark.integration


def test_projectless_event_identity_serializes_conflicting_concurrent_delivery(disposable_url):
    from scope_guard.database.repositories.activity import EventRepository
    from scope_guard.database.repositories.profiles import Profiles
    from scope_guard.domain.activity import ActivityEvent, EventConflict

    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        database = Database(normalize_url(disposable_url))
        try:
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("concurrent@example.test", "synthetic")
                profile = await Profiles(work.session).get(owner.id)
                await work.commit()

            async def deliver(operation):
                try:
                    async with database.new_uow() as work:
                        await EventRepository(work.session).append(
                            ActivityEvent(
                                profile_id=profile["id"],
                                actor_user_id=owner.id,
                                operation_id=operation,
                                event_type="profile.updated",
                                source="profile",
                                deduplication_key="same-logical-key",
                                payload={"revision": "2"},
                            )
                        )
                        await work.commit()
                    return "saved"
                except EventConflict:
                    return "conflict"

            assert sorted(await asyncio.gather(deliver(uuid4()), deliver(uuid4()))) == [
                "conflict",
                "saved",
            ]
            async with database.new_uow() as work:
                assert (
                    await work.session.scalar(
                        text(
                            "SELECT count(*) FROM activity_events WHERE "
                            "deduplication_key='same-logical-key'"
                        )
                    )
                    == 1
                )
        finally:
            await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_forced_precommit_failure_rolls_back_project_revision_and_event(
    disposable_url, monkeypatch
):
    from scope_guard.database.repositories.workflow import WorkflowSQLRepository, WorkflowUnitOfWork
    from scope_guard.services.drafts.workflow import WorkflowService

    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        database = Database(normalize_url(disposable_url))
        try:
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("rollback@example.test", "synthetic")
                await work.commit()
            original = WorkflowSQLRepository.event

            async def fail_after_event(self, *args, **kwargs):
                await original(self, *args, **kwargs)
                raise RuntimeError("forced_precommit_failure")

            monkeypatch.setattr(WorkflowSQLRepository, "event", fail_after_event)
            service = WorkflowService(lambda: WorkflowUnitOfWork(database.new_uow()))
            with pytest.raises(RuntimeError, match="forced_precommit_failure"):
                await service.create_project(
                    owner.id,
                    {
                        "operationId": str(uuid4()),
                        "name": "Rolled back",
                        "industry": "Development",
                        "scope": "Original scope",
                        "startDate": "2026-10-01",
                        "pricingModel": "hourly",
                        "currency": "USD",
                        "hourlyRate": "30",
                        "fixedPrice": None,
                    },
                )
            async with database.new_uow() as work:
                for table in ("projects", "drafts", "draft_revisions"):
                    assert await work.session.scalar(text(f"SELECT count(*) FROM {table}")) == 0
                assert (
                    await work.session.scalar(
                        text(
                            "SELECT count(*) FROM activity_events "
                            "WHERE event_type='project.created'"
                        )
                    )
                    == 0
                )
        finally:
            await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_authenticated_profile_api_and_browser_sessions(disposable_url):
    import httpx
    from pydantic import SecretStr
    from scope_guard_api.main import create_app

    from scope_guard.core.config import Settings

    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic-profile-test"),
                workflow_v2=True,
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                assert (await client.get("/api/v2/profile")).status_code == 401
                body = {"email": "api@example.test", "password": "synthetic-password"}
                registered = await client.post("/api/auth/register", json=body)
                assert registered.status_code == 201
                from uuid import UUID

                from scope_guard.database.repositories.users import AuthUnitOfWork
                from scope_guard.integrations.auth.passwords import Passwords
                from scope_guard.services.auth.tokens import AuthTokenService

                confirmation = AuthTokenService(
                    lambda: AuthUnitOfWork(app.state.database.new_uow()), Passwords()
                )
                owner_id = UUID(registered.json()["user"]["id"])
                link = await confirmation.issue_pending_confirmation(owner_id)
                await confirmation.confirm_email(owner_id, link.raw)
                assert "scg_browser" in client.cookies
                # Upgrade: concurrent tabs share an existing authentication cookie,
                # but no product-browser cookie has yet reached either tab.
                old_auth = client.cookies.get("scg_session")
                # Frontend hydration is serialized across tabs using Web Locks;
                # cookies set by the first response are browser-wide.
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app),
                    base_url="http://test",
                    cookies={"scg_session": old_auth},
                ) as hydration:
                    assert (await hydration.get("/api/auth/me")).status_code == 200
                    assert hydration.cookies.get("scg_browser") is not None
                    tab_cookies = dict(hydration.cookies)
                async with (
                    httpx.AsyncClient(
                        transport=httpx.ASGITransport(app),
                        base_url="http://test",
                        cookies=tab_cookies,
                    ) as tab_a,
                    httpx.AsyncClient(
                        transport=httpx.ASGITransport(app),
                        base_url="http://test",
                        cookies=tab_cookies,
                    ) as tab_b,
                ):
                    hydrated = await asyncio.gather(
                        tab_a.get("/api/auth/me"), tab_b.get("/api/auth/me")
                    )
                    assert all(response.status_code == 200 for response in hydrated)
                    assert tab_a.cookies.get("scg_browser") is not None
                    assert tab_a.cookies["scg_browser"] == tab_b.cookies["scg_browser"]
                    observed = await asyncio.gather(
                        tab_a.post("/api/v2/session/interaction"),
                        tab_b.post("/api/v2/session/interaction"),
                    )
                    assert all(response.status_code == 204 for response in observed)
                    async with app.state.database.new_uow() as work:
                        assert (
                            await work.session.scalar(text("SELECT count(*) FROM product_sessions"))
                            == 2
                        )
                profile = (await client.get("/api/v2/profile")).json()["profile"]
                assert "analyticsExcluded" not in profile
                update = {
                    "operationId": str(uuid4()),
                    "expectedRevision": "1",
                    "changes": {"profession": "Designer", "preferences": {"locale": "en"}},
                }
                first = await client.patch("/api/v2/profile", json=update)
                assert first.status_code == 200, first.text
                for _ in range(2):
                    assert (
                        await client.patch("/api/v2/profile", json=update)
                    ).json() == first.json()
                assert (
                    await client.patch(
                        "/api/v2/profile", json={**update, "changes": {"analyticsExcluded": True}}
                    )
                ).status_code == 400
                async with app.state.database.new_uow() as work:
                    before = await work.session.scalar(
                        text("SELECT max(last_activity_at) FROM product_sessions")
                    )
                for _ in range(3):
                    await client.get("/api/v2/profile")
                    await client.patch("/api/v2/profile", json=update)
                async with app.state.database.new_uow() as work:
                    assert (
                        await work.session.scalar(
                            text("SELECT max(last_activity_at) FROM product_sessions")
                        )
                        == before
                    )
                assert (await client.post("/api/v2/session/interaction")).status_code == 204
                async with app.state.database.new_uow() as work:
                    assert (
                        await work.session.scalar(
                            text("SELECT max(last_activity_at) FROM product_sessions")
                        )
                        > before
                    )
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app), base_url="http://test"
                ) as other_browser:
                    assert (
                        await other_browser.post("/api/auth/login", json=body)
                    ).status_code == 200
                    assert other_browser.cookies["scg_browser"] != client.cookies["scg_browser"]
                async with app.state.database.new_uow() as work:
                    assert (
                        await work.session.scalar(text("SELECT count(*) FROM product_sessions"))
                        == 3
                    )

    asyncio.run(exercise())
    engine.dispose()


def test_registration_profile_cas_events_and_sessions(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        from scope_guard.database.repositories.activity import EventRepository
        from scope_guard.database.repositories.profiles import Profiles
        from scope_guard.database.repositories.sessions import ProductSessions
        from scope_guard.domain.activity import ActivityEvent, EventConflict
        from scope_guard.domain.drafts.workflow import WorkflowError

        database = Database(normalize_url(disposable_url))
        try:
            async with database.new_uow() as work:
                await Users(work.session).insert("rolled-back@example.test", "synthetic")
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("profile@example.test", "synthetic")
                other = await Users(work.session).insert("other@example.test", "synthetic")
                profile = await Profiles(work.session).get(owner.id)
                assert profile["revision"] == "1"
                assert profile["preferences"]["locale"] is None
                await work.commit()
            operation = uuid4()
            changes = {"displayName": "Designer", "preferences": {"timezone": "Europe/Moscow"}}
            async with database.new_uow() as work:
                repository = Profiles(work.session)
                result = await repository.update(owner.id, 1, operation, changes)
                for _ in range(2):
                    assert await repository.update(owner.id, 1, operation, changes) == result
                with pytest.raises(WorkflowError, match="operationMismatch"):
                    await repository.update(owner.id, 1, operation, {"displayName": "Changed"})
                with pytest.raises(WorkflowError, match="profileConflict"):
                    await repository.update(owner.id, 1, uuid4(), changes)
                assert (await repository.get(other.id))["displayName"] is None
                await work.commit()
            now = datetime.now(UTC)
            async with database.new_uow() as work:
                sessions = ProductSessions(work.session)
                session = await sessions.resolve(profile["id"], "a" * 64, now=now)
                assert await sessions.resolve(profile["id"], "a" * 64, now=now) == session
                assert await sessions.resolve(profile["id"], "b" * 64, now=now) != session
                successor = await sessions.resolve(
                    profile["id"], "a" * 64, now=now + timedelta(minutes=30)
                )
                assert successor != session
                event = ActivityEvent(
                    profile_id=profile["id"],
                    actor_user_id=owner.id,
                    operation_id=uuid4(),
                    event_type="profile.updated",
                    source="profile",
                    deduplication_key=str(uuid4()),
                    payload={"revision": "2"},
                )
                events = EventRepository(work.session)
                first = await events.append(event)
                assert await events.append(event) == first
                with pytest.raises(EventConflict):
                    await events.append(replace(event, payload={"revision": "3"}))
                assert work.session.info["marketing_metrics_dirty"] is True
                await work.commit()
        finally:
            await database.close()

    asyncio.run(exercise())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == 2
        assert connection.scalar(text("SELECT count(*) FROM profiles")) == 2
        assert connection.scalar(text("SELECT count(*) FROM profile_preferences")) == 2
        assert connection.scalar(text("SELECT count(*) FROM profile_revisions")) == 3
        assert (
            connection.scalar(
                text("SELECT count(*) FROM activity_events WHERE event_type='profile.created'")
            )
            == 2
        )
        assert (
            connection.scalar(text("SELECT bool_and(event_version=2) FROM activity_events")) is True
        )
    engine.dispose()


def test_durable_admission_deadline_and_publication_events(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        from uuid import UUID

        from scope_guard.database.repositories.llm import LlmSQLStore
        from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
        from scope_guard.services.activity.context import browser_key
        from scope_guard.services.drafts.workflow import WorkflowService
        from scope_guard.services.llm.operations import LlmOperations

        database = Database(normalize_url(disposable_url))
        try:

            def factory():
                return WorkflowUnitOfWork(database.new_uow())

            async with database.new_uow() as work:
                owner = await Users(work.session).insert("llm@example.test", "synthetic")
                await work.commit()
            workflow = WorkflowService(factory)
            project = await workflow.create_project(
                owner.id,
                {
                    "operationId": str(uuid4()),
                    "name": "Project",
                    "industry": "Development",
                    "scope": "Original scope",
                    "startDate": "2026-10-01",
                    "pricingModel": "hourly",
                    "currency": "USD",
                    "hourlyRate": "30",
                    "fixedPrice": None,
                },
            )
            draft = await workflow.project_draft(owner.id, UUID(project["id"]))
            draft = await workflow.save(
                owner.id,
                UUID(draft["id"]),
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": draft["revision"],
                    "changes": {"requestText": "Add a report"},
                },
            )
            store = LlmSQLStore(database.new_uow)
            policy = {
                "model": "gpt-5.4-nano",
                "inputRate": "0.000001",
                "outputRate": "0.000002",
                "maxCost": "0.000001",
                "maxCalls": 12,
                "durationSeconds": 180,
            }
            operations = LlmOperations(
                factory, store, policy, language_selector=lambda *args: {"selectedLanguage": "en"}
            )
            token = browser_key.set("d" * 64)
            command = {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "locale": "en",
            }
            try:
                failed = await operations.admit(owner.id, UUID(draft["id"]), "check", command)
                for _ in range(2):
                    assert (
                        await operations.admit(owner.id, UUID(draft["id"]), "check", command)
                        == failed
                    )
                assert failed["status"] == "failed"
                policy["maxCost"] = "1.00"
                queued = await operations.admit(
                    owner.id, UUID(draft["id"]), "check", {**command, "operationId": str(uuid4())}
                )
            finally:
                browser_key.reset(token)
            async with database.new_uow() as work:
                await work.session.execute(
                    text(
                        "UPDATE llm_operations SET deadline_at=now()-interval '1 second' "
                        "WHERE id=:id"
                    ),
                    {"id": queued["operationId"]},
                )
                await work.commit()
            assert await store.claim("test-worker") is None
            assert await store.claim("test-worker") is None
            async with database.new_uow() as work:
                events = (
                    (
                        await work.session.execute(
                            text(
                                "SELECT event_type,actor_type,product_session_id FROM "
                                "activity_events "
                                "WHERE event_type LIKE 'check.%' ORDER BY created_at,id"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                assert [e["event_type"] for e in events].count("check.requested") == 2
                assert [e["event_type"] for e in events].count("check.failed") == 2
                assert all(e["product_session_id"] is not None for e in events)
                assert all(
                    e["actor_type"] == "system" for e in events if e["event_type"] == "check.failed"
                )
        finally:
            await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_workflow_new_events_and_legacy_receipt_bridge(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")

    async def exercise():
        from uuid import UUID

        from scope_guard.database.repositories.activity import EventRepository
        from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
        from scope_guard.domain.activity import ActivityEvent, EventConflict
        from scope_guard.services.activity.context import browser_key
        from scope_guard.services.drafts.workflow import WorkflowService

        database = Database(normalize_url(disposable_url))
        try:
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("workflow@example.test", "synthetic")
                await work.commit()
            service = WorkflowService(lambda: WorkflowUnitOfWork(database.new_uow()))
            body = {
                "operationId": str(uuid4()),
                "name": "Project",
                "industry": "Development",
                "scope": "Original scope",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
                "hourlyRate": "30",
                "fixedPrice": None,
            }
            token = browser_key.set("c" * 64)
            try:
                project = await service.create_project(owner.id, body)
                assert project["profileId"]
                for _ in range(2):
                    assert (await service.create_project(owner.id, body))["id"] == project["id"]
                draft = await service.project_draft(owner.id, UUID(project["id"]))
                for _ in range(3):
                    draft = await service.save(
                        owner.id,
                        UUID(draft["id"]),
                        {
                            "operationId": str(uuid4()),
                            "expectedRevision": draft["revision"],
                            "reason": "language_change",
                            "changes": {"requestText": "New request"},
                        },
                    )
                async with database.new_uow() as work:
                    session_before = await work.session.scalar(
                        text("SELECT last_activity_at FROM product_sessions WHERE profile_id=:id"),
                        {"id": project["profileId"]},
                    )
                await service.save(
                    owner.id,
                    UUID(draft["id"]),
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": draft["revision"],
                        "reason": "autosave",
                        "changes": {"requestText": "Automatic save"},
                    },
                )
                async with database.new_uow() as work:
                    assert (
                        await work.session.scalar(
                            text(
                                "SELECT last_activity_at FROM product_sessions WHERE profile_id=:id"
                            ),
                            {"id": project["profileId"]},
                        )
                        == session_before
                    )
                    assert (
                        await work.session.scalar(
                            text(
                                "SELECT count(*) FROM activity_events WHERE "
                                "event_type='draft.updated'"
                            )
                        )
                        == 4
                    )
                    assert (
                        await work.session.scalar(
                            text(
                                "SELECT count(*) FROM activity_events WHERE "
                                "event_type='project.created'"
                            )
                        )
                        == 1
                    )
                    row = (
                        await work.session.execute(
                            text(
                                "SELECT translation_succeeded,operations_succeeded "
                                "FROM marketing_metrics "
                                "WHERE report_date=(now() AT TIME ZONE 'UTC')::date"
                            )
                        )
                    ).one()
                    assert row.translation_succeeded == row.operations_succeeded == 0
                    operation = uuid4()
                    legacy_id = await work.session.scalar(
                        text(
                            "INSERT INTO "
                            "activity_events(project_id,operation_id,event_type,actor_type,"
                            "actor_user_id,payload,payload_version) "
                            "VALUES(:project,:op,'agreement_voided',"
                            "'user',:owner,'{}',1) RETURNING id"
                        ),
                        {"project": project["id"], "op": operation, "owner": owner.id},
                    )
                    event = ActivityEvent(
                        profile_id=project["profileId"],
                        project_id=project["id"],
                        operation_id=operation,
                        event_type="change_order.voided",
                        source="workflow",
                        deduplication_key=f"{project['id']}:{operation}:change_order.voided",
                        actor_user_id=owner.id,
                        legacy_event_type="agreement_voided",
                    )
                    assert await EventRepository(work.session).append(event) == legacy_id
                    with pytest.raises(EventConflict):
                        await EventRepository(work.session).append(
                            replace(event, payload={"revision": "2"})
                        )
                    await work.commit()
            finally:
                browser_key.reset(token)
        finally:
            await database.close()

    asyncio.run(exercise())
    engine.dispose()
