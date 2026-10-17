"""Generation outcomes survive cancellation at the T1/T2 boundary."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.users import Users
from scope_guard.database.repositories.workflow import WorkflowSQLRepository, WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.analysis.normalization import parse_materials, parse_snapshot
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.marketing.service import MetricsService

pytestmark = pytest.mark.integration
FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())


@pytest.mark.parametrize("kind", ["regenerate", "translate"])
@pytest.mark.parametrize("interruption", ["postcommit", "provider_cancel", "precommit"])
def test_generation_terminal_outcome_matches_committed_receipt(
    disposable_url, monkeypatch, kind, interruption
):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")
    engine.dispose()

    async def exercise():
        database = Database(normalize_url(disposable_url))
        reached, blocked = asyncio.Event(), asyncio.Event()
        generation_task = None

        class Generator:
            calls = 0

            async def analyze(self, value):
                return parse_snapshot(FIXTURE["analysis"], "en")

            async def generated(self):
                self.calls += 1
                assert database.engine.pool.checkedout() == 0
                if interruption == "provider_cancel":
                    reached.set()
                    await blocked.wait()

            async def regenerate_reply(self, value):
                await self.generated()
                return "Regenerated reply"

            async def translate_materials(self, value):
                await self.generated()
                return parse_materials(
                    {
                        "clientLanguage": "ru",
                        "replies": {tone: "Ответ" for tone in ("warm", "neutral", "firm")},
                        "changeOrder": {
                            "description": "Условия",
                            "timelineImpact": "Два дня",
                            "rationale": "",
                            "note": "Примечание",
                        },
                    }
                )

        generator = Generator()
        service = WorkflowService(lambda: WorkflowUnitOfWork(database.new_uow()), generator)
        try:
            async with database.new_uow() as work:
                owner = await Users(work.session).insert("cancel@example.test", "synthetic")
                await work.commit()
            project = await service.create_project(
                owner.id, {**FIXTURE["projectInput"], "operationId": str(uuid4())}
            )
            draft = await service.project_draft(owner.id, UUID(project["id"]))
            identifier = UUID(draft["id"])

            def command(state):
                return {"expectedRevision": state["revision"], "operationId": str(uuid4())}

            draft = await service.save(
                owner.id,
                identifier,
                {**command(draft), "changes": {"requestText": "Add a page"}},
            )
            draft = (
                await service.analyze(owner.id, identifier, {**command(draft), "locale": "en"})
            )["draft"]
            body = {**command(draft), "language": "ru"}
            operation = UUID(body["operationId"])
            original_reconcile = database._reconcile_metrics
            callbacks = 0

            async def reconcile():
                nonlocal callbacks
                callbacks += 1
                if interruption == "postcommit" and callbacks == 2:
                    # Requested is commit1; the completed write is commit2.
                    assert database.engine.pool.checkedout() == 0
                    reached.set()
                    await blocked.wait()
                await original_reconcile()

            monkeypatch.setattr(database, "_reconcile_metrics", reconcile)
            original_save = WorkflowSQLRepository.save

            async def fail_before_commit(repository, *args, **kwargs):
                await original_save(repository, *args, **kwargs)
                raise RuntimeError("forced_precommit_failure")

            if interruption == "precommit":
                monkeypatch.setattr(WorkflowSQLRepository, "save", fail_before_commit)

            async def persisted():
                async with database.new_uow() as work:
                    revision = await work.session.scalar(
                        text("SELECT revision FROM drafts WHERE id=:id"), {"id": identifier}
                    )
                    receipts = await work.session.scalar(
                        text("SELECT count(*) FROM draft_revisions WHERE operation_id=:op"),
                        {"op": operation},
                    )
                    events = (
                        await work.session.scalars(
                            text("SELECT event_type FROM activity_events WHERE operation_id=:op"),
                            {"op": operation},
                        )
                    ).all()
                    return revision, receipts, events

            generation_task = asyncio.create_task(
                service.generate(owner.id, identifier, kind, body)
            )
            if interruption == "precommit":
                with pytest.raises(RuntimeError, match="forced_precommit_failure"):
                    await generation_task
            else:
                await asyncio.wait_for(reached.wait(), timeout=10)
                if interruption == "postcommit":
                    committed_revision, receipts, _ = await persisted()
                    assert committed_revision == int(draft["revision"]) + 1
                    assert receipts == 1
                generation_task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await generation_task

            revision, receipts, events = await persisted()
            prefix = "reply" if kind == "regenerate" else "translation"
            completed = "reply.regenerated" if kind == "regenerate" else "translation.completed"
            assert events.count(prefix + ".requested") == 1
            if interruption == "postcommit":
                assert events.count(completed) == 1
                assert prefix + ".failed" not in events
                assert receipts == 1 and revision == int(draft["revision"]) + 1
                retried = await service.generate(owner.id, identifier, kind, body)
                assert retried["revision"] == str(revision)
                assert await persisted() == (revision, receipts, events)
            else:
                assert events.count(prefix + ".failed") == 1
                assert completed not in events
                assert receipts == 0 and revision == int(draft["revision"])
            assert generator.calls == 1

            # Interrupted T2 repairs on supported access; it must agree with T1.
            today = datetime.now(UTC).date()
            rows = await MetricsService(database.new_metrics_uow).read(
                today, today + timedelta(days=1)
            )
            metric = "regeneration" if kind == "regenerate" else "translation"
            assert rows[0][metric + "_succeeded"] == (interruption == "postcommit")
            assert rows[0][metric + "_failed"] == (interruption != "postcommit")
        finally:
            if generation_task is not None and not generation_task.done():
                generation_task.cancel()
                await asyncio.gather(generation_task, return_exceptions=True)
            await database.close()

    asyncio.run(exercise())
