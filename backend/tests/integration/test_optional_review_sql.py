"""Real SQL, frozen operations and physical-call accounting; never a real provider."""

import asyncio
import json
from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from integration.test_llm_pipeline import output
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore, LlmTransactionRepository
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.llm.runtime import Binding, GatewayFailure, ProviderResponse, digest, encode
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


async def prepare(url, enabled=True, mode="clean", expect_job=True):
    engine = create_engine(normalize_url(url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) "
                "VALUES ('review@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")
    engine.dispose()
    database = Database(normalize_url(url))

    def factory():
        return WorkflowUnitOfWork(database.new_uow())

    store = LlmSQLStore(database.new_uow, semantic_review_enabled=enabled)
    workflow = WorkflowService(factory)
    project = await workflow.create_project(
        owner,
        {
            "operationId": str(uuid4()),
            "name": "Review fixture",
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
            "model": "controlled",
            "inputRate": ".000001",
            "outputRate": ".000002",
            "maxCost": "1",
            "durationSeconds": 180,
        },
        language_selector=select,
    )
    calls = []

    class Adapter:
        async def request(self, request, timeout):
            calls.append(request)
            if request.schema_name == "semantic_review_v2":
                if mode == "inflight_disabled":
                    store.semantic_review_enabled = False
                if mode == "retry_disabled":
                    store.semantic_review_enabled = False
                    raise ConnectionError("controlled transport failure")
                if mode == "outage":
                    raise RuntimeError("private provider details")
                if mode == "malformed":
                    return ProviderResponse("{broken", input_tokens=10, output_tokens=5)
                value = (
                    {"decision": "accept", "violations": []}
                    if mode != "findings"
                    else {
                        "decision": "reject",
                        "violations": [
                            {"field": "warm", "rule": "facts", "feedback": "Unsupported statement."}
                        ],
                    }
                )
                return ProviderResponse(
                    json.dumps(value),
                    model="actual-controlled",
                    provider="double",
                    response_id="response-test",
                    request_id="request-test",
                    input_tokens=10,
                    output_tokens=5,
                    reported_cost=Decimal("2") if mode == "overrun" else None,
                )
            return ProviderResponse(
                json.dumps(output(request.schema_name, "en", "en")),
                input_tokens=100,
                output_tokens=25,
            )

    runner = StructuredStageRunner(
        ProviderGateway(store, Adapter()), store, semantic_review_enabled=enabled
    )
    worker = LlmWorker(factory, store, runner, semantic_review_enabled=enabled)
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
    assert await worker.process_one()
    parent_id = UUID(pending["operationId"])
    parent = await store.get(owner, parent_id)
    assert parent["status"] == "succeeded", parent
    async with database.engine.connect() as connection:
        row = (
            (await connection.execute(text("SELECT * FROM llm_operations WHERE kind='diagnostic'")))
            .mappings()
            .one_or_none()
        )
        job = dict(row) if row else None
    assert (job is not None) == expect_job
    return database, owner, draft_id, workflow, store, runner, worker, parent, job, calls


@pytest.mark.parametrize(
    "mode,enabled,want,review_calls",
    [
        ("clean", False, "skipped_disabled", 0),
        ("clean", True, "completed_clean", 1),
        ("findings", True, "completed_findings", 1),
        ("outage", True, "failed", 1),
        ("malformed", True, "failed", 1),
        ("retry_disabled", True, "skipped_disabled", 1),
        ("budget", True, "skipped_budget", 0),
        ("version", True, "unavailable_version", 0),
        ("historical", True, "skipped_disabled", 0),
        ("runtime_false", True, "skipped_disabled", 0),
        ("dispatch_false", True, "skipped_disabled", 0),
        ("inflight_disabled", True, "completed_clean", 1),
    ],
)
def test_optional_review_sql_outcomes_and_source_isolation(
    disposable_url, mode, enabled, want, review_calls
):
    async def exercise():
        (
            database,
            owner,
            draft_id,
            workflow,
            store,
            runner,
            worker,
            parent,
            job,
            calls,
        ) = await prepare(disposable_url, enabled, mode)
        try:
            if mode in {"historical", "version"}:
                frozen = deepcopy(job["frozen_input"])
                if mode == "historical":
                    frozen.pop("semanticReview")
                else:
                    frozen["semanticReview"]["promptVersion"] = "future-review"
                async with database.engine.begin() as connection:
                    await connection.execute(
                        text(
                            "UPDATE llm_operations SET frozen_input=CAST(:input AS jsonb),"
                            "input_hash=:hash WHERE id=:id"
                        ),
                        {"id": job["id"], "input": encode(frozen), "hash": digest(frozen)},
                    )
            if mode == "budget":
                async with database.engine.begin() as connection:
                    await connection.execute(
                        text(
                            "UPDATE llm_operations SET "
                            "policy=jsonb_set(policy,'{maxCost}','\"0\"') WHERE id=:id"
                        ),
                        {"id": job["id"]},
                    )
            if mode == "runtime_false":
                runner.semantic_review_enabled = store.semantic_review_enabled = False
            if mode == "dispatch_false":
                store.semantic_review_enabled = False
            # A user edit after generation must not become review input or be overwritten.
            draft = await workflow.draft(owner, draft_id)
            await workflow.save(
                owner,
                draft_id,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": draft["revision"],
                    "changes": {"requestText": "Later manual request."},
                },
            )
            saved = await workflow.draft(owner, draft_id)
            history = await workflow.histories(owner, parent["project_id"])
            assert await worker.process_one(lane="diagnostic")
            finished = await store.get(owner, job["id"])
            assert finished["status"] == "succeeded", finished
            results = {r["stage"]: r for r in finished["result"]["reviews"]}
            assert results["analysis"]["outcome"] == "skipped_unsupported"
            assert results["replies"]["outcome"] == want
            assert len([c for c in calls if c.schema_name == "semantic_review_v2"]) == review_calls
            assert (await store.get(owner, parent["id"])) == parent
            assert (await workflow.draft(owner, draft_id)) == saved
            assert (await workflow.histories(owner, parent["project_id"])) == history
            steps = await store.steps(job["id"])
            assert all(s["status"] == "accepted" for s in steps)
            assert any(s["accepted_result"].get("observations") for s in steps)
            async with database.engine.connect() as connection:
                ledger = (
                    (
                        await connection.execute(
                            text("SELECT * FROM provider_calls WHERE operation_id=:id"),
                            {"id": job["id"]},
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(ledger) == review_calls
                assert (
                    await connection.scalar(
                        text("SELECT count(*) FROM llm_operations WHERE kind='diagnostic'")
                    )
                    == 1
                )
                if want.startswith("completed"):
                    call = ledger[0]
                    assert (
                        call["requested_model"] == "controlled"
                        and call["actual_model"] == "actual-controlled"
                    )
                    assert (
                        call["response_id"] == "response-test"
                        and call["provider_request_id"] == "request-test"
                    )
                    assert call["input_tokens"] == 10 and call["output_tokens"] == 5
                    assert finished["spent"] > 0
                if mode == "malformed":
                    assert ledger[0]["validation_status"] == "rejected"
            # Restart after local work and accepted review, before operation completion.
            if want.startswith("completed"):
                async with database.engine.begin() as connection:
                    await connection.execute(
                        text(
                            "UPDATE llm_operations SET status='queued',finished_at=NULL "
                            "WHERE id=:id"
                        ),
                        {"id": job["id"]},
                    )
                assert await worker.process_one(lane="diagnostic")
                assert len([c for c in calls if c.schema_name == "semantic_review_v2"]) == 1
            assert not await worker.process_one(lane="diagnostic")
        finally:
            await database.close()

    asyncio.run(exercise())


def test_actual_cost_overrun_retains_failed_ledger_without_failing_parent(disposable_url):
    async def exercise():
        database, owner, _, _, store, _, worker, parent, job, _ = await prepare(
            disposable_url, mode="overrun"
        )
        try:
            assert await worker.process_one(lane="diagnostic")
            failed = await store.get(owner, job["id"])
            assert failed["status"] == "failed"
            assert failed["error"]["code"] == "errors.operationBudgetExceeded"
            assert failed["spent"] == Decimal("2")
            assert await store.get(owner, parent["id"]) == parent
            async with database.engine.connect() as connection:
                call = (
                    (
                        await connection.execute(
                            text("SELECT * FROM provider_calls WHERE operation_id=:id"),
                            {"id": job["id"]},
                        )
                    )
                    .mappings()
                    .one()
                )
            assert failed["error"]["callId"] == str(call["id"])
            assert call["reported_cost"] == Decimal("2")
            assert call["error"]["code"] == "providerCostBoundExceeded"
            assert not await worker.process_one(lane="diagnostic")
        finally:
            await database.close()

    asyncio.run(exercise())


def test_diagnostic_writes_require_current_lease_even_without_budget(disposable_url):
    async def exercise():
        database, owner, _, _, store, _, _, _, job, _ = await prepare(disposable_url)
        try:
            claimed = await store.claim("current", lane="diagnostic")
            step = (await store.steps(job["id"]))[0]
            stale = Binding(job["id"], step["id"], claimed["epoch"] - 1, "controlled", "medium")
            with pytest.raises(GatewayFailure, match="operationLeaseLost"):
                await store.diagnostic_result(stale, {"outcome": "skipped_disabled"})
            with pytest.raises(GatewayFailure, match="operationLeaseLost"):
                await store.finish_diagnostics({**claimed, "epoch": stale.epoch})
        finally:
            await database.close()

    asyncio.run(exercise())


def test_enqueue_failure_rolls_back_only_diagnostics(disposable_url, monkeypatch):
    original = LlmTransactionRepository.enqueue_diagnostics

    async def fail_after_insert(self, operation, **kwargs):
        await original(self, operation, **kwargs)
        raise RuntimeError("controlled diagnostic insertion failure")

    monkeypatch.setattr(LlmTransactionRepository, "enqueue_diagnostics", fail_after_insert)

    async def exercise():
        database, *_ = await prepare(disposable_url, expect_job=False)
        try:
            async with database.engine.connect() as connection:
                rows = (
                    await connection.execute(text("SELECT kind,status FROM llm_operations"))
                ).all()
                assert rows == [("check", "succeeded")]
        finally:
            await database.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("checkpoint", ["candidate", "unknown"])
def test_restart_recovers_received_candidate_but_never_redispatches_unknown(
    disposable_url, monkeypatch, checkpoint
):
    async def exercise():
        database, owner, _, _, store, runner, worker, _, job, calls = await prepare(disposable_url)
        original = store.accept

        async def interrupted_accept(binding, value):
            raise asyncio.CancelledError()

        monkeypatch.setattr(store, "accept", interrupted_accept)
        try:
            with pytest.raises(asyncio.CancelledError):
                await worker.process_one(lane="diagnostic")
            assert len([c for c in calls if c.schema_name == "semantic_review_v2"]) == 1
            if checkpoint == "unknown":
                async with database.engine.begin() as connection:
                    await connection.execute(
                        text(
                            "UPDATE llm_steps SET candidate=NULL WHERE operation_id=:id "
                            "AND stage_key='replies_review_1'"
                        ),
                        {"id": job["id"]},
                    )
                    # A crash before durable receipt retains its unknown reservation.
                    await connection.execute(
                        text(
                            "UPDATE provider_calls SET status='unknown',usage_status='unknown',"
                            "cost_status='unknown' WHERE operation_id=:id"
                        ),
                        {"id": job["id"]},
                    )
            monkeypatch.setattr(store, "accept", original)
            # Runtime false still permits recovery of already received work.
            store.semantic_review_enabled = runner.semantic_review_enabled = False
            assert await worker.process_one(lane="diagnostic")
            result = (await store.get(owner, job["id"]))["result"]["reviews"]
            review = next(r for r in result if r["stage"] == "replies")
            assert review["outcome"] == (
                "completed_clean" if checkpoint == "candidate" else "failed"
            )
            if checkpoint == "unknown":
                assert review["reason"] == "diagnosticOutcomeUnknown"
            assert len([c for c in calls if c.schema_name == "semantic_review_v2"]) == 1
        finally:
            await database.close()

    asyncio.run(exercise())
