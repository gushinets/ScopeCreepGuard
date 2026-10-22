"""Real PostgreSQL migration compatibility, isolation, persistence and concurrent tabs."""

import asyncio

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.profiles import ProfilesUnitOfWork
from scope_guard.database.repositories.users import Users
from scope_guard.database.session import Database, normalize_url
from scope_guard.services.profiles.service import ProfileService

pytestmark = pytest.mark.integration


def test_existing_profiles_are_exempt_new_profiles_are_eligible(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0007_nonblocking_llm")
        connection.exec_driver_sql("SET LOCAL search_path TO public")
        owner = connection.exec_driver_sql(
            "INSERT INTO users(email,password_hash) VALUES "
            "('existing@example.test','synthetic') RETURNING id"
        ).scalar_one()
        connection.execute(text("INSERT INTO profiles(user_id) VALUES(:id)"), {"id": owner})
        migrate(connection, target="head")
        assert connection.exec_driver_sql(
            "SELECT onboarding_status,onboarding_step FROM profiles"
        ).one() == ("completed", 4)
    engine.dispose()


def test_persistence_isolation_and_terminal_concurrency(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")
    engine.dispose()

    async def exercise():
        database = Database(normalize_url(disposable_url))
        service = ProfileService(lambda: ProfilesUnitOfWork(database.new_uow()))
        try:
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("new@example.test", "synthetic")
                other = await Users(work.session).insert("other@example.test", "synthetic")
                await work.commit()
            assert await service.onboarding(owner.id) == {"status": "not_started", "step": 0}
            for event in ("form_opened", "project_saved", "check_submitted", "result_viewed"):
                await service.onboarding(owner.id, event)
            await asyncio.gather(
                service.onboarding(owner.id, "form_opened"),
                service.onboarding(owner.id, "project_saved"),
                service.onboarding(owner.id, "skip"),
            )
            assert await service.onboarding(owner.id) == {"status": "completed", "step": 4}
            assert await service.onboarding(other.id) == {"status": "not_started", "step": 0}
            await asyncio.gather(
                service.onboarding(other.id, "skip"),
                service.onboarding(other.id, "form_opened"),
            )
            assert (await service.onboarding(other.id))["status"] == "skipped"
        finally:
            await database.close()

    asyncio.run(exercise())
