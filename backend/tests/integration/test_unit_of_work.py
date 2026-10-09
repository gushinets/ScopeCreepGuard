import asyncio

import pytest
from integration.support import replay_drizzle
from sqlalchemy import text

pytestmark = pytest.mark.integration


def test_commit_rollback_reuse_and_pool_return(disposable_url):
    from scope_guard.core.config import Settings
    from scope_guard.infrastructure.database.session import create_database

    replay_drizzle(disposable_url)

    async def exercise():
        database = create_database(Settings(_env_file=None, database_url=disposable_url))
        try:
            async with database.new_uow() as uow:
                await uow.session.execute(
                    text(
                        "CREATE TABLE commit_failure(value int UNIQUE "
                        "DEFERRABLE INITIALLY DEFERRED)"
                    )
                )
                await uow.commit()
            from sqlalchemy.exc import IntegrityError

            with pytest.raises(IntegrityError):
                async with database.new_uow() as uow:
                    await uow.session.execute(text("INSERT INTO commit_failure VALUES (1),(1)"))
                    await uow.commit()
            async with database.new_uow() as uow:
                assert (
                    await uow.session.execute(text("SELECT count(*) FROM commit_failure"))
                ).scalar() == 0
            async with database.new_uow() as uow:
                await uow.session.execute(
                    text("INSERT INTO users(email,password_hash) VALUES ('commit@test','hash')")
                )
                await uow.commit()
            async with database.new_uow() as uow:
                await uow.session.execute(
                    text("INSERT INTO users(email,password_hash) VALUES ('rollback@test','hash')")
                )
            with pytest.raises(ValueError):
                async with database.new_uow() as uow:
                    await uow.session.execute(
                        text(
                            "INSERT INTO users(email,password_hash) VALUES "
                            "('exception@test','hash')"
                        )
                    )
                    raise ValueError("injected")
            with pytest.raises(asyncio.CancelledError):
                async with database.new_uow() as uow:
                    await uow.session.execute(
                        text("INSERT INTO users(email,password_hash) VALUES ('cancel@test','hash')")
                    )
                    raise asyncio.CancelledError()
            async with database.new_uow() as read:
                assert (
                    await read.session.execute(text("SELECT email FROM users"))
                ).scalars().all() == ["commit@test"]
            with pytest.raises(RuntimeError, match="uow_finished"):
                async with read:
                    pass
            assert database.engine.pool.checkedout() == 0
        finally:
            await database.close()

    asyncio.run(exercise())
