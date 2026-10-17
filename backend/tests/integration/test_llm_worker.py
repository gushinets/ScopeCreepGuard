"""Worker owns execution and publication independently of the admitting request."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.change_orders.constants import LABEL_KEYS
from scope_guard.integrations.llm.detection import select
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("target", ["0007_nonblocking_llm", "head"])
def test_worker_publishes_once_and_preserves_late_edit(disposable_url, target):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('worker@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target=target)

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        workflow, store = WorkflowService(factory), LlmSQLStore(database.new_uow)
        policy = {
            "model": "gpt-5.4-nano",
            "inputRate": ".000001",
            "outputRate": ".000002",
            "maxCost": "1",
            "durationSeconds": 180,
            "version": "workflow-policy-v1",
        }
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": "Historical project",
                "industry": "Development",
                "startDate": "2026-10-01",
                "scope": "Arrow and email are excluded.",
                "currency": "USD",
                "pricingModel": "hourly",
                "hourlyRate": "30.00",
                "fixedPrice": None,
            },
        )
        draft = await workflow.project_draft(owner, UUID(project["id"]))
        draft_id = UUID(draft["id"])
        draft = await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"requestText": "Add Arrow and email alerts."},
            },
        )
        operations = LlmOperations(factory, store, policy, language_selector=select)
        command = {
            "operationId": str(uuid4()),
            "expectedRevision": draft["revision"],
            "locale": "en",
        }
        pending = await operations.admit(owner, draft_id, "check", command)
        stages = []

        class Runner:
            async def diagnose(self, operation):
                await store.finish_diagnostics(operation)

            async def run(self, binding, stage, facts, record):
                stages.append(stage)
                if stage == "reply":
                    return {"text": "The additional scope requires approval."}
                if stage == "estimate":
                    return {
                        "estimatedHours": "8",
                        "additionalCost": "240.00",
                        "currency": "USD",
                        "rationale": "Eight hours at thirty dollars.",
                    }
                if stage == "analysis":
                    assert database.engine.pool.checkedout() == 0
                    return {
                        "verdict": "out_of_scope",
                        "confidence": 95,
                        "summary": "The client asks for additional work.",
                        "reasoning": "Arrow and email are excluded.",
                        "citations": ["Arrow and email are excluded."],
                        "suggestion": "Prepare a separate estimate.",
                        "hasAdditionalWork": True,
                        "estimatedHours": 8,
                        "additionalCost": "240.00",
                        "currency": "USD",
                    }
                if stage == "replies":
                    return {
                        "scopePosition": "out_of_scope",
                        **dict.fromkeys(
                            ("warm", "neutral", "firm"),
                            "These additions are outside the agreed scope "
                            "and require a separate estimate.",
                        ),
                    }
                return {
                    "scopePosition": "out_of_scope",
                    "applicable": True,
                    "description": "Add Arrow and email alerts.",
                    "timelineImpact": "Subject to separate approval.",
                    "rationale": "Eight additional hours at the agreed hourly rate.",
                    "note": "This is a draft, not legal advice.",
                    "additionalTerms": "",
                    "labels": dict.fromkeys(LABEL_KEYS, "Change order"),
                }

        # Originating HTTP request has finished. A separate worker claims from PostgreSQL.
        worker = LlmWorker(factory, store, Runner())
        assert await worker.process_one()
        status = await operations.status(owner, UUID(pending["operationId"]))
        assert status["status"] == "succeeded"
        assert set(stages) == {"analysis", "replies"}
        assert status["result"]["applied"] is True
        histories = await workflow.histories(owner, UUID(project["id"]))
        assert len(histories) == 1
        # A separate queued diagnostic job does not change user-operation status.
        assert await worker.process_one(lane="diagnostic")
        assert (await operations.admit(owner, draft_id, "check", command))[
            "operationId"
        ] == pending["operationId"]

        # Another command may create a check, but cannot replace a later request/edit.
        draft = await workflow.draft(owner, draft_id)
        pending = await operations.admit(
            owner,
            draft_id,
            "check",
            {**command, "operationId": str(uuid4()), "expectedRevision": draft["revision"]},
        )
        changed = await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"requestText": "A newer request."},
            },
        )
        assert await worker.process_one()
        status = await operations.status(owner, UUID(pending["operationId"]))
        assert status["status"] == "succeeded" and status["result"]["applied"] is False
        assert (await workflow.draft(owner, draft_id))["requestText"] == changed["requestText"]
        assert len(await workflow.histories(owner, UUID(project["id"]))) == 2
        history = (await workflow.histories(owner, UUID(project["id"])))[-1]
        reopened = await workflow.reopen_history(
            owner,
            UUID(history["id"]),
            {"operationId": str(uuid4()), "expectedRevision": changed["revision"]},
        )
        assert reopened["requestText"] == "Add Arrow and email alerts."
        assert reopened["draftDocument"]["reply"]["language"] == "en"
        assert (await workflow.history(owner, UUID(history["id"])))["checkSnapshot"] == history[
            "checkSnapshot"
        ]
        if target == "head":
            for _ in range(3):
                await workflow.evaluate(
                    owner, UUID(history["analysisRunId"]), {"accuracy": "correct"}
                )
            await workflow.evaluate(
                owner, UUID(history["analysisRunId"]), {"accuracy": "debatable"}
            )
            async with database.new_uow() as work:
                events = (
                    (
                        await work.session.execute(
                            text("SELECT * FROM activity_events WHERE event_type='check.completed'")
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(events) == 2
                assert {e["payload"]["applied"] for e in events} == {True, False}
                assert all(e["history_entry_id"] and e["actor_type"] == "system" for e in events)
                assert (
                    await work.session.scalar(
                        text(
                            "SELECT count(*) FROM activity_events "
                            "WHERE event_type='evaluation.changed'"
                        )
                    )
                    == 2
                )
                assert await work.session.scalar(text("SELECT count(*) FROM evaluation_cases")) == 1
            for kind in ("agreement", "regenerate", "translate", "estimate"):
                latest = await workflow.draft(owner, draft_id)
                admitted = await operations.admit(
                    owner,
                    draft_id,
                    kind,
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": latest["revision"],
                        "language": "ru",
                    },
                )
                assert await worker.process_one()
                outcome = await operations.status(owner, UUID(admitted["operationId"]))
                assert outcome["status"] == "succeeded", outcome
            async with database.new_uow() as work:
                names = (
                    (await work.session.execute(text("SELECT event_type FROM activity_events")))
                    .scalars()
                    .all()
                )
                for name in ("reply.regenerated", "translation.completed", "estimate.completed"):
                    assert names.count(name) == 1
                metrics = (
                    (
                        await work.session.execute(
                            text(
                                "SELECT * FROM marketing_metrics "
                                "WHERE report_date=(now() AT TIME ZONE 'UTC')::date"
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                assert metrics["check_succeeded"] == 2
                assert metrics["regeneration_succeeded"] == 1
                assert metrics["translation_succeeded"] == 1
                assert metrics["estimate_succeeded"] == 1
                assert (
                    metrics["operations_succeeded"] == 6
                )  # includes the explicit agreement command
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
