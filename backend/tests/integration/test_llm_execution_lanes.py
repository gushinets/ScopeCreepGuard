"""Production composition/run with real PostgreSQL, native gateway and provider barriers."""

import asyncio
import importlib.util
import json
import multiprocessing
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from integration.test_llm_pipeline import output
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.llm.runtime import ProviderResponse
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("review", ["accept", "reject", "failure", "cancel"])
def test_production_main_keeps_user_lane_available(disposable_url, monkeypatch, review):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('lane@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")
    engine.dispose()

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        store, workflow = LlmSQLStore(database.new_uow), WorkflowService(factory)
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": "Monitor",
                "industry": "Development",
                "scope": "Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
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
        operations = LlmOperations(
            factory,
            store,
            {
                "version": "workflow-policy-v1",
                "model": "gpt-5.4-nano",
                "inputRate": ".000001",
                "outputRate": ".000002",
                "maxCost": "1",
                "durationSeconds": 180,
            },
            language_selector=select,
        )
        events, calls = [], []
        diagnostic_entered, release, user_entered = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        published = asyncio.Queue()
        signals, instances = {}, []

        class Adapter:
            active = 0
            maximum = 0
            closed = False

            async def request(self, request, timeout):
                calls.append(request.schema_name)
                if request.schema_name == "semantic_review_v2":
                    self.active += 1
                    self.maximum = max(self.maximum, self.active)
                    try:
                        events.append("diagnostic blocked")
                        diagnostic_entered.set()
                        await release.wait()
                        if review == "failure":
                            raise RuntimeError("controlled diagnostic failure")
                        value = {"decision": "accept", "violations": []}
                        if review == "reject":
                            value = {
                                "decision": "reject",
                                "violations": [
                                    {
                                        "field": "warm",
                                        "rule": "scope_position",
                                        "feedback": "Frozen scope",
                                    }
                                ],
                            }
                    finally:
                        self.active -= 1
                else:
                    if request.schema_name == "reply_v1":
                        events.append("user provider entered")
                        user_entered.set()
                    value = output(request.schema_name, "en", "en")
                return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=25)

            async def close(self):
                self.closed = True

        adapter = Adapter()

        class ObservedWorker(LlmWorker):
            def __init__(self, *args, **kwargs):
                super().__init__(
                    *args,
                    **kwargs,
                    poll_interval=0.02,
                    heartbeat_interval=0.02,
                    shutdown_timeout=0.05,
                )
                instances.append(self)

            async def execute(self, operation):
                try:
                    await super().execute(operation)
                finally:
                    await published.put(operation)

        # Invoke apps/worker/main.py itself; only infrastructure/provider injection
        # and observation change. Scheduling/claims/execution/accounting are production.
        spec = importlib.util.spec_from_file_location(
            "lane_composition", Path(__file__).parents[3] / "apps/worker/main.py"
        )
        composition = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(composition)
        monkeypatch.setattr(
            composition,
            "Settings",
            lambda: SimpleNamespace(
                worker_role="llm",
                llm_workflow=True,
                workflow_v2=True,
                openai_api_key=SecretStr("controlled"),
            ),
        )
        monkeypatch.setattr(composition, "create_database", lambda settings: database)
        monkeypatch.setattr(
            "scope_guard.integrations.llm.litellm_adapter.LiteLLMResponsesAdapter",
            lambda key: adapter,
        )
        monkeypatch.setattr("scope_guard.services.llm.worker.LlmWorker", ObservedWorker)
        monkeypatch.setattr(
            asyncio.get_running_loop(),
            "add_signal_handler",
            lambda sig, fn: signals.update({sig: fn}),
        )
        main = await operations.admit(
            owner,
            draft_id,
            "check",
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "locale": "en",
            },
        )
        running = asyncio.create_task(composition.main())
        try:
            await asyncio.wait_for(diagnostic_entered.wait(), 30)
            assert (await operations.status(owner, UUID(main["operationId"])))[
                "status"
            ] == "succeeded"
            # A second independent worker/store may claim neither held diagnostic
            # nor completed user job, including attempts with the wrong lane.
            peer = LlmSQLStore(database.new_uow)
            assert await peer.claim("peer-user", lane="user") is None
            assert await peer.claim("peer-review", lane="diagnostic") is None
            draft = await workflow.draft(owner, draft_id)
            pending = await operations.admit(
                owner,
                draft_id,
                "regenerate",
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": draft["revision"],
                },
            )
            events.append("user operation admitted")
            await asyncio.wait_for(user_entered.wait(), 10)
            while (operation := await asyncio.wait_for(published.get(), 10))[
                "kind"
            ] != "regenerate":
                pass
            status = await operations.status(owner, UUID(pending["operationId"]))
            assert status["status"] == "succeeded", status
            assert not release.is_set()
            events.append("user operation succeeded")
            saved = deepcopy((await workflow.draft(owner, draft_id))["draftDocument"])
            main_snapshot = deepcopy(
                (await operations.status(owner, UUID(main["operationId"])))["result"]
            )
            diagnostic = await store.get(owner, operation["id"])
            assert diagnostic["kind"] == "regenerate"
            if review == "cancel":
                instances[0].stopping.set()
                await asyncio.wait_for(running, 10)
                assert adapter.active == 0 and adapter.closed
                async with database.new_uow() as work:
                    unknown = (
                        (
                            await work.session.execute(
                                text("SELECT * FROM provider_calls WHERE status='unknown'")
                            )
                        )
                        .mappings()
                        .all()
                    )
                assert len(unknown) == 1
                assert unknown[0]["error"]["code"] == "providerOutcomeUnknown"
                assert unknown[0]["reserved_cost"] > 0
                old_review_calls = calls.count("semantic_review_v2")
                release.set()
                # Reclaim expired/abandoned diagnostics. Attempted review is never
                # dispatched again; the new regeneration review is allowed once.
                recovery = LlmWorker(
                    factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
                )
                assert await recovery.process_one(lane="diagnostic")
                assert calls.count("semantic_review_v2") == old_review_calls
                assert await recovery.process_one(lane="diagnostic")
                assert not await recovery.process_one(lane="diagnostic")
            else:
                events.append("diagnostic released")
                release.set()
                while (operation := await asyncio.wait_for(published.get(), 10))[
                    "kind"
                ] != "diagnostic":
                    pass
                instances[0].stopping.set()
                await asyncio.wait_for(running, 10)
            assert (await operations.status(owner, UUID(pending["operationId"])))[
                "result"
            ] == status["result"]
            assert (await operations.status(owner, UUID(main["operationId"])))[
                "result"
            ] == main_snapshot
            assert (await workflow.draft(owner, draft_id))["draftDocument"] == saved
            assert adapter.maximum == 1 and adapter.active == 0 and adapter.closed
            async with database.new_uow() as work:
                records = (
                    (
                        await work.session.execute(
                            text(
                                "SELECT c.status,c.usage_status,c.estimated_cost,"
                                "c.reserved_cost,o.kind "
                                "FROM provider_calls c JOIN llm_operations o ON o.id=c.operation_id"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            assert all(row["status"] != "in_flight" for row in records)
            assert any(row["kind"] == "diagnostic" and row["reserved_cost"] > 0 for row in records)
            assert (
                calls.count("analysis_v1")
                == calls.count("replies_v1")
                == calls.count("reply_v1")
                == 1
            )
            print(
                "LANE_EVIDENCE "
                + json.dumps(
                    {
                        "review": review,
                        "events": events,
                        "calls": calls,
                        "accounting": [
                            dict(
                                row,
                                estimated_cost=str(row["estimated_cost"]),
                                reserved_cost=str(row["reserved_cost"]),
                            )
                            for row in records
                        ],
                    }
                )
            )
        finally:
            release.set()
            if instances:
                instances[0].stopping.set()
            if not running.done():
                running.cancel()
            await asyncio.gather(running, return_exceptions=True)
            await database.close()

    asyncio.run(exercise())


def _competing_worker(url, start, release, results):
    """An actual separate worker process holds execution behind a process barrier."""
    from scope_guard.database.session import event_loop

    async def exercise():
        database = Database(normalize_url(url))
        store = LlmSQLStore(database.new_uow)

        class Worker(LlmWorker):
            async def execute(self, operation):
                results.put(("entered", str(operation["id"])))
                await asyncio.to_thread(release.wait)

        try:
            worker = Worker(None, store, None)
            results.put(("returned", await worker.process_one()))
        finally:
            await database.close()

    start.wait()
    asyncio.run(exercise(), loop_factory=event_loop)


def test_two_processes_cannot_execute_same_claim(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('race@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")

    async def admit():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        workflow, store = WorkflowService(factory), LlmSQLStore(database.new_uow)
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": "Claim race",
                "industry": "Development",
                "scope": "Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
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
        operations = LlmOperations(
            factory,
            store,
            {
                "version": "workflow-policy-v1",
                "model": "gpt-5.4-nano",
                "inputRate": ".000001",
                "outputRate": ".000002",
                "maxCost": "1",
                "durationSeconds": 180,
            },
            language_selector=select,
        )
        pending = await operations.admit(
            owner,
            draft_id,
            "check",
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "locale": "en",
            },
        )
        # A diagnostic lane must leave a queued user command untouched, even
        # when it is the only available work.
        assert await store.claim("diagnostic-only", lane="diagnostic") is None
        await database.close()
        return pending["operationId"]

    identifier = asyncio.run(admit())
    context = multiprocessing.get_context("spawn")
    start, release, results = context.Event(), context.Event(), context.Queue()
    children = [
        context.Process(target=_competing_worker, args=(disposable_url, start, release, results))
        for _ in range(2)
    ]
    try:
        for child in children:
            child.start()
        start.set()
        # One process executes and stays held; the other must return without
        # executing. Both observations are required before releasing the winner.
        observed = [results.get(timeout=30), results.get(timeout=30)]
        assert sorted(observed) == [("entered", identifier), ("returned", False)]
        release.set()
        assert results.get(timeout=10) == ("returned", True)
        for child in children:
            child.join(timeout=10)
            assert child.exitcode == 0
    finally:
        release.set()
        for child in children:
            if child.is_alive():
                child.terminate()
            child.join(timeout=10)
        results.close()
        engine.dispose()
