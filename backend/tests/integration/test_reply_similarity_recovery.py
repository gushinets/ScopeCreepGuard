"""Regeneration retry recovery and publication on owned disposable PostgreSQL."""

import asyncio
import json
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from integration.test_llm_pipeline import output
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.llm.runtime import GatewayFailure, ProviderResponse
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "mode",
    [
        "similar",
        "long",
        "cached_long",
        "malformed",
        "no_valid",
        "restart",
        "cached",
        "cached_final",
        "provider_error",
        "accept_error",
        "late_edit",
    ],
)
def test_regeneration_durable_fallback_and_publication(disposable_url, mode):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('novelty@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")
    engine.dispose()

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        workflow = WorkflowService(factory)
        store = LlmSQLStore(database.new_uow)
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
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": "Novelty test",
                "industry": "Development",
                "scope": "Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
                "hourlyRate": "30.00",
                "fixedPrice": None,
            },
        )
        project_id = UUID(project["id"])
        draft = await workflow.project_draft(owner, project_id)
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
        previous, pending_id = None, None
        requests = []
        entered = asyncio.Event()
        interrupt = mode == "restart"
        cache_interrupt = mode in ("cached", "cached_final", "cached_long")

        class Adapter:
            async def request(self, request, timeout):
                nonlocal interrupt
                requests.append(request)
                if request.schema_name == "reply_v1":
                    user = next(m["content"] for m in request.messages if m["role"] == "user")
                    # Restart prompts append saved validation feedback after source JSON.
                    assert (
                        json.JSONDecoder().raw_decode(user)[0]["previousReply"]["text"] == previous
                    )
                    if interrupt and request.semantic_attempt == 2:
                        interrupt = False
                        entered.set()
                        await asyncio.Event().wait()
                    if mode == "provider_error" and request.semantic_attempt == 2:
                        raise RuntimeError("controlled provider failure")
                    if mode == "no_valid" or (
                        mode in ("malformed", "restart") and request.semantic_attempt == 3
                    ):
                        payload = "{invalid JSON"
                    else:
                        payload = json.dumps(
                            {
                                "scopePosition": "out_of_scope",
                                "text": "Please authorize a proposal for Arrow integration."
                                if mode == "accept_error"
                                else "ba " * 1000
                                if mode in ("long", "cached_long")
                                else previous
                                + " "
                                + ("Thanks.", "Thank you.", "Much appreciated.")[
                                    request.semantic_attempt - 1
                                ],
                            }
                        )
                else:
                    value = output(request.schema_name, "en", "en")
                    if request.schema_name == "change_order_v1":
                        value.pop("labels", None)
                    payload = json.dumps(value)
                return ProviderResponse(payload, input_tokens=100, output_tokens=25)

        adapter = Adapter()
        worker = LlmWorker(
            factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
        )

        async def admit(kind):
            current = await workflow.draft(owner, draft_id)
            return await operations.admit(
                owner,
                draft_id,
                kind,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": current["revision"],
                    "locale": "en",
                },
            )

        for kind in ("check", "agreement"):
            admitted = await admit(kind)
            assert await worker.process_one()
            assert (await operations.status(owner, UUID(admitted["operationId"])))[
                "status"
            ] == "succeeded"
        current = await workflow.draft(owner, draft_id)
        # A selected manual edit is the reference, not the generated slot.
        document = deepcopy(current["draftDocument"])
        document["reply"]["text"] += " Please send written approval."
        if mode in ("long", "cached_long"):
            document["reply"]["text"] = "ab " * 1000
        await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": current["revision"],
                "changes": {"draftDocument": document},
            },
        )
        before = await workflow.draft(owner, draft_id)
        history = deepcopy(await workflow.histories(owner, project_id))
        previous = before["draftDocument"]["reply"]["text"]
        pending = await admit("regenerate")
        pending_id = UUID(pending["operationId"])
        frozen = deepcopy((await store.get(owner, pending_id))["frozen_input"])

        if mode == "accept_error":

            async def fail_acceptance(binding, value):
                raise GatewayFailure("operationBudgetExceeded")

            store.accept = fail_acceptance

        complete = store.complete

        async def pause_after_checkpoint(identifier, response=None, error=None):
            nonlocal cache_interrupt
            await complete(identifier, response=response, error=error)
            call = await store.call(identifier)
            target = 3 if mode == "cached_final" else 1
            if cache_interrupt and call["semantic_attempt"] == target and response:
                cache_interrupt = False
                entered.set()
                await asyncio.Event().wait()

        if cache_interrupt:
            store.complete = pause_after_checkpoint
        if mode in ("restart", "cached", "cached_final", "cached_long"):
            running = asyncio.create_task(worker.process_one())
            await asyncio.wait_for(entered.wait(), 30)
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
            step = (await store.steps(pending_id))[0]
            assert step["status"] != "accepted" and step["accepted_result"] is None
            if mode == "restart":
                assert step["candidate"] is None
                assert step["feedback"]["novelty"]["candidate"]["text"] == previous + " Thanks."
                assert step["semantic_attempt"] == 2
            # A new store and runner must recover all state from PostgreSQL.
            store = LlmSQLStore(database.new_uow)
            worker = LlmWorker(
                factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
            )
        if mode == "late_edit":
            await workflow.save(
                owner,
                draft_id,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": before["revision"],
                    "patch": {"reply.text": "A newer user edit"},
                },
            )
        assert await worker.process_one()
        operation = await store.get(owner, pending_id)
        status = await operations.status(owner, pending_id)
        step = (await store.steps(pending_id))[0]
        after = await workflow.draft(owner, draft_id)
        regen_calls = [r for r in requests if r.schema_name == "reply_v1"]
        assert max(r.semantic_attempt for r in regen_calls) <= 3
        assert operation["frozen_input"] == frozen
        assert await workflow.histories(owner, project_id) == history
        assert after["analysisRun"] == before["analysisRun"]
        assert after["draftDocument"]["changeOrder"] == before["draftDocument"]["changeOrder"]
        for tone in ("warm", "firm"):
            assert (
                after["draftDocument"]["reply"]["generated"][tone]
                == before["draftDocument"]["reply"]["generated"][tone]
            )
        if mode in ("no_valid", "provider_error", "accept_error", "late_edit"):
            assert status["status"] == "failed", status
            if mode == "accept_error":
                assert status["error"]["code"] == "errors.operationBudgetExceeded"
                assert "rule" not in step["feedback"]
            if mode != "late_edit":
                assert after["draftDocument"] == before["draftDocument"]
            else:
                assert after["draftDocument"]["reply"]["text"] == "A newer user edit"
        else:
            assert status["status"] == "succeeded", (status.get("error"), step, regen_calls)
            expected = previous + (
                " Thank you." if mode in ("malformed", "restart") else " Much appreciated."
            )
            if mode in ("long", "cached_long"):
                expected = "ba " * 1000
            assert after["draftDocument"]["reply"]["text"] == expected
            assert after["draftDocument"]["reply"]["generated"]["neutral"] == expected
            novelty = step["feedback"]["novelty"]
            assert "candidate" not in novelty
            if mode in ("long", "cached_long"):
                assert novelty["exhausted"] is False and novelty["score"] is None
                assert novelty["skippedReason"] == "comparison_limit"
                assert novelty["comparisonLimit"] == 2048 and novelty["attempt"] == 1
            else:
                assert novelty["exhausted"] is True and novelty["score"] >= 0.72
                assert novelty["attempt"] == (2 if mode in ("malformed", "restart") else 3)
            assert novelty["threshold"] == 0.72
            from scope_guard.domain.llm.runtime import Binding
            from scope_guard.integrations.llm.diagnostics import local_observations

            observations = local_observations(
                Binding(pending_id, step["id"], operation["epoch"], "model", "high"),
                "reply",
                step["accepted_result"],
                frozen,
                novelty=novelty,
            )
            finding = next(o for o in observations if o.rule == "reply_similarity")
            if mode in ("long", "cached_long"):
                assert finding.outcome == "uncertain"
                assert finding.skipped_reason == "comparison_limit"
                assert finding.comparison_limit == 2048
            else:
                assert finding.outcome == "finding" and finding.novelty_exhausted is True
            assert finding.score == novelty["score"]
        async with database.new_uow() as work:
            calls = (
                (
                    await work.session.execute(
                        text(
                            "SELECT * FROM provider_calls WHERE operation_id=:id "
                            "ORDER BY physical_index"
                        ),
                        {"id": pending_id},
                    )
                )
                .mappings()
                .all()
            )
        assert (
            len(calls)
            == len(regen_calls)
            == (
                4
                if mode == "restart"
                else 2
                if mode == "provider_error"
                else 1
                if mode in ("accept_error", "long", "cached_long")
                else 3
            )
        )
        assert operation["physical_calls"] == len(calls)
        assert all(c["input_tokens"] == 100 for c in calls if c["status"] == "completed")
        if mode in ("malformed", "restart"):
            assert calls[-1]["validation_status"] == "rejected"
            assert calls[-2]["validation_status"] == "accepted"
        await database.close()

    asyncio.run(exercise())
