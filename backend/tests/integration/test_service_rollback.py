import asyncio
from uuid import uuid4

import pytest
from integration.support import prepare_alembic
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.database.models import ProjectRow, UserRow
from scope_guard.database.repositories.projects import Projects, ProjectUnitOfWork
from scope_guard.database.session import create_database
from scope_guard.domain.projects.domain import ManualHistoryInput
from scope_guard.domain.shared.enums import Industry, Verdict
from scope_guard.services.projects.use_cases import ProjectError, ProjectService

pytestmark = pytest.mark.integration


def test_failing_write_use_case_rolls_back_inserted_history(disposable_url, monkeypatch):
    prepare_alembic(disposable_url)

    async def fail_after_history(*args):
        return False

    monkeypatch.setattr(Projects, "update_last_checked", fail_after_history)

    async def run():
        database = create_database(Settings(_env_file=None, database_url=disposable_url))
        assert database is not None
        owner, identifier = uuid4(), uuid4()
        try:
            async with database.new_uow() as work:
                work.session.add(
                    UserRow(id=owner, email="rollback@example.test", password_hash="test")
                )
                await work.session.flush()
                work.session.add(
                    ProjectRow(
                        id=identifier,
                        user_id=owner,
                        name="Project",
                        scope="Scope",
                        industry=Industry.Development,
                    )
                )
                await work.commit()

            async def entry():
                return ManualHistoryInput("2026-01-01", "Request", Verdict.in_scope, "Summary")

            service = ProjectService(lambda: ProjectUnitOfWork(database.new_uow()))
            with pytest.raises(ProjectError, match="projectNotFound"):
                await service.create_history(str(owner), str(identifier), entry)
            async with database.engine.connect() as connection:
                assert (await connection.scalar(text("SELECT count(*) FROM history_entries"))) == 0
                assert (await connection.scalar(text("SELECT last_checked FROM projects"))) is None
        finally:
            await database.close()

    asyncio.run(run())
