import asyncio

import pytest
from integration.support import prepare_alembic
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scope_guard.database.repositories.password_recovery import RecoveryLimited, RecoveryQueue
from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


def test_address_and_source_hourly_windows_and_reset_limits(disposable_url):
    prepare_alembic(disposable_url, target="head")

    async def run():
        engine = create_async_engine(
            disposable_url.replace("postgresql://", "postgresql+psycopg://")
        )
        sessions = async_sessionmaker(engine)
        queue = RecoveryQueue(lambda: SqlAlchemyUnitOfWork(sessions), "test")

        async def expire(pattern):
            async with sessions.begin() as db:
                await db.execute(
                    text(
                        "UPDATE recovery_limits SET "
                        "expires_at=clock_timestamp()-interval '1 second' "
                        "WHERE id LIKE :pattern"
                    ),
                    {"pattern": pattern},
                )

        try:
            for _ in range(4):
                await expire("address-minute:%")
                await queue.request("unknown@example.test", "en", "address-test")
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 3
            await expire("address-%")
            await queue.request("unknown@example.test", "en", "address-test")
            async with sessions() as db:
                assert await db.scalar(text("SELECT count(*) FROM email_jobs")) == 4
            for index in range(60):
                await expire("request:60:%")
                await queue.request(f"missing-{index}@example.test", "en", "hour-source")
            await expire("request:60:%")
            with pytest.raises(RecoveryLimited):
                await queue.request("missing-last@example.test", "en", "hour-source")
            await expire("request:3600:%")
            await queue.request("missing-last@example.test", "en", "hour-source")
            for _ in range(30):
                await queue.reset_limit("reset-source")
            with pytest.raises(RecoveryLimited):
                await queue.reset_limit("reset-source")
            await expire("reset:900:%")
            await queue.reset_limit("reset-source")
            async with sessions.begin() as db:
                await db.execute(
                    text("UPDATE recovery_limits SET count=1000 WHERE id='request:global-hour'")
                )
            with pytest.raises(RecoveryLimited):
                await queue.request("known-or-unknown@example.test", "en", "fresh-source")
            async with sessions.begin() as db:
                await db.execute(
                    text("UPDATE recovery_limits SET count=300 WHERE id='reset:global-minute'")
                )
            with pytest.raises(RecoveryLimited):
                await queue.reset_limit("fresh-reset-source")
        finally:
            await engine.dispose()

    asyncio.run(run())
