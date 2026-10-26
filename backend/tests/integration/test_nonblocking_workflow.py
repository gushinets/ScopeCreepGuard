"""Controlled provider, real native contracts/queue/PostgreSQL; no paid calls."""

import asyncio
import json
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from integration.test_llm_pipeline import output
from scope_guard_api.draft_input import parse_editor
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.llm.runtime import ProviderResponse
from scope_guard.integrations.documents.preparation import prepare_document
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("pricing_changed", [False, True])
def test_main_agreement_diagnostics_and_concurrency(disposable_url, pricing_changed):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('nonblocking@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        workflow, store = WorkflowService(factory), LlmSQLStore(database.new_uow)
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
        calls = []
        fail_agreement = False

        class Adapter:
            async def request(self, request, timeout):
                calls.append(request)
                assert request.schema_name != "semantic_review_v2"
                if request.schema_name == "change_order_v1" and fail_agreement:
                    raise RuntimeError("controlled agreement outage")
                else:
                    value = output(request.schema_name, "en", "en")
                    if request.schema_name == "reply_v1":
                        value["text"] += " Please confirm the separate proposal in writing."
                    if request.schema_name == "replies_v1":
                        value["warm"] += " Сроки согласуем отдельно."
                    if request.schema_name == "change_order_v1":
                        value["note"] = "This change order is a draft and is not legal advice."
                        value.pop("labels", None)
                return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=25)

        runner = StructuredStageRunner(ProviderGateway(store, Adapter()), store)
        worker = LlmWorker(factory, store, runner)

        async def admit(kind, current, **extra):
            body = {"operationId": str(uuid4()), "expectedRevision": current["revision"], **extra}
            pending = await operations.admit(owner, draft_id, kind, body)
            return pending, body

        pending, command = await admit("check", draft, locale="en")
        assert await worker.process_one()
        status = await operations.status(owner, UUID(pending["operationId"]))
        assert status["status"] == "succeeded", status
        assert [c.schema_name for c in calls] == ["analysis_v1", "replies_v1"]
        assert status["result"]["draft"]["draftDocument"]["changeOrder"] is None
        assert status["result"]["analysisRun"]["resultSnapshot"]["changeOrder"] is None
        assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
        assert (await operations.admit(owner, draft_id, "check", command))[
            "operationId"
        ] == pending["operationId"]
        # Local diagnostics run after publication and make no provider requests.
        calls_before_diagnostics = len(calls)
        assert await worker.process_one(lane="diagnostic")
        assert (await operations.status(owner, UUID(pending["operationId"])))[
            "status"
        ] == "succeeded"
        assert (await workflow.draft(owner, draft_id))["draftDocument"]["reply"]["text"]
        assert len(calls) == calls_before_diagnostics
        assert (await operations.status(owner, UUID(pending["operationId"])))[
            "status"
        ] == "succeeded"
        # Explicit action only. Failure cannot erase the saved response/history.
        draft = await workflow.draft(owner, draft_id)
        await workflow.update_project(
            owner,
            UUID(project["id"]),
            {
                **project,
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "hourlyRate": "60.00" if pricing_changed else "30.00",
                "name": "Updated project",
                "clientName": "Updated client",
                "clientEmail": "updated@example.test",
                "endDate": "2026-12-31",
            },
        )
        draft = await workflow.draft(owner, draft_id)
        assert draft["analysisIsStale"] is False
        fail_agreement = True
        agreement, body = await admit("agreement", draft)
        await worker.process_one()
        assert (await operations.status(owner, UUID(agreement["operationId"])))[
            "status"
        ] == "failed"
        assert (await workflow.draft(owner, draft_id))["draftDocument"] == draft["draftDocument"]
        fail_agreement = False
        agreement, body = await admit("agreement", draft)
        duplicate, _ = await admit("agreement", draft)
        assert duplicate["operationId"] == agreement["operationId"]
        await worker.process_one()
        status = await operations.status(owner, UUID(agreement["operationId"]))
        assert status["status"] == "succeeded", status
        draft = await workflow.draft(owner, draft_id)
        assert (
            draft["draftDocument"]["changeOrder"]["note"]
            == "This change order is a draft and is not legal advice."
        )
        assert (await operations.admit(owner, draft_id, "agreement", body))[
            "operationId"
        ] == agreement["operationId"]
        order = draft["draftDocument"]["changeOrder"]
        assert order["additionalCost"] == ("480.00" if pricing_changed else "240.00")
        assert order["projectName"] == "Updated project"
        assert order["clientName"] == "Updated client"
        assert order["clientEmail"] == "updated@example.test"
        assert order["endDate"] == "2026-12-31"
        from scope_guard.domain.change_orders.estimation import commercial_signature
        from scope_guard.services.drafts.workflow import generation_context

        current_project = await workflow.project(owner, UUID(project["id"]))
        provenance = draft["draftDocument"]["estimate"]
        assert provenance["estimateValid"] is True
        assert provenance["commercialSignature"] == commercial_signature(
            generation_context(project["id"], current_project), order["endDate"]
        )
        assert provenance["effectiveEndDate"] == order["endDate"]
        assert draft["analysisRun"]["projectSnapshot"]["name"] == "Monitor"
        assert draft["analysisRun"]["resultSnapshot"]["estimate"]["additionalCost"] == "240.00"
        calls_before_diagnostics = len(calls)
        assert await worker.process_one(lane="diagnostic")
        assert len(calls) == calls_before_diagnostics
        count = len(calls)
        reopened, _ = await admit("agreement", draft)
        assert (await operations.status(owner, UUID(reopened["operationId"])))[
            "status"
        ] == "succeeded"
        assert len(calls) == count
        with pytest.raises(WorkflowError):
            await operations.status(uuid4(), UUID(pending["operationId"]))
        # A rate-only edit can archive accepted manual terms without reclassification.
        manual = deepcopy(draft["draftDocument"])
        manual["changeOrder"].update(additionalCost="175.35", currency="USD", estimatedHours="2.50")
        draft = await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"draftDocument": manual},
            },
        )
        await workflow.update_project(
            owner,
            UUID(project["id"]),
            {
                **project,
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "hourlyRate": "80.00",
                "currency": "EUR",
            },
        )
        draft = await workflow.draft(owner, draft_id)
        assert draft["analysisIsStale"] is False
        if not pricing_changed:
            # Durable free/paid edits change presentation without clearing source,
            # revising the original analysis/History, or dispatching generation.
            histories_before = deepcopy(await workflow.histories(owner, UUID(project["id"])))
            analysis_before = deepcopy(draft["analysisRun"])
            free_document = deepcopy(draft["draftDocument"])
            free_document["changeOrder"].update(
                noAdditionalCharge=True,
                rationale="2.5 hours × 80 EUR = 200 EUR.",
            )
            command = {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"draftDocument": free_document},
            }
            saved = await workflow.save(owner, draft_id, command)
            assert (await workflow.save(owner, draft_id, command))["revision"] == saved["revision"]
            reloaded = await workflow.draft(owner, draft_id)
            co = reloaded["draftDocument"]["changeOrder"]
            assert co == free_document["changeOrder"]
            assert co["additionalCost"] == "175.35" and co["currency"] == "USD"
            free = prepare_document(parse_editor(co))
            assert free.commercial[1].value == "No additional charge"
            assert all(row.label != free.label("rationale") for row in free.additional)
            with pytest.raises(WorkflowError, match="draftConflict"):
                await workflow.save(owner, draft_id, {**command, "operationId": str(uuid4())})
            paid_document = deepcopy(reloaded["draftDocument"])
            paid_document["changeOrder"]["noAdditionalCharge"] = False
            await workflow.save(
                owner,
                draft_id,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": reloaded["revision"],
                    "changes": {"draftDocument": paid_document},
                },
            )
            draft = await workflow.draft(owner, draft_id)
            paid = prepare_document(parse_editor(draft["draftDocument"]["changeOrder"]))
            assert paid.commercial[1].value == "175.35 USD"
            assert any(row.value == co["rationale"] for row in paid.additional)
            assert draft["analysisRun"] == analysis_before
            assert await workflow.histories(owner, UUID(project["id"])) == histories_before
            assert len(calls) == count
        archived = await workflow.complete(
            owner, draft_id, {"operationId": str(uuid4()), "expectedRevision": draft["revision"]}
        )
        assert (
            archived["checkSnapshot"]["draftDocument"]["changeOrder"]["additionalCost"] == "175.35"
        )
        # Reopen the automatic History result with its latest saved materials, no generation.
        first_history = (await workflow.histories(owner, UUID(project["id"])))[-1]
        reopened = await workflow.reopen_history(
            owner,
            UUID(first_history["id"]),
            {"operationId": str(uuid4()), "expectedRevision": draft["revision"]},
        )
        assert reopened["draftDocument"]["changeOrder"]["additionalCost"] == "175.35"
        assert len(calls) == count
        draft = await workflow.draft(owner, draft_id)
        await workflow.update_project(
            owner,
            UUID(project["id"]),
            {
                **project,
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "scope": "A genuinely changed scope",
            },
        )
        draft = await workflow.draft(owner, draft_id)
        assert draft["analysisIsStale"] is True
        with pytest.raises(WorkflowError, match="analysisStale"):
            await workflow.complete(
                owner,
                draft_id,
                {"operationId": str(uuid4()), "expectedRevision": draft["revision"]},
            )
        # A real admission/worker/provider round trip preserves all other saved state.
        before = deepcopy(draft)
        regen_ok, regen_command = await admit("regenerate", draft)
        frozen_row = await store.get(owner, UUID(regen_ok["operationId"]))
        frozen_before = deepcopy(frozen_row["frozen_input"])
        assert frozen_before["currentCommercialTerms"]["additionalCost"] == "175.35"
        assert frozen_before["currentCommercialTerms"]["currency"] == "USD"
        assert await worker.process_one()
        assert (await operations.status(owner, UUID(regen_ok["operationId"])))[
            "status"
        ] == "succeeded"
        sent = json.loads(next(m["content"] for m in calls[-1].messages if m["role"] == "user"))
        assert sent["currentCommercialTerms"] == frozen_before["currentCommercialTerms"]
        assert sent["scopeContext"]["scope"] == frozen_before["project"]["scope"]
        assert "genuinely changed" not in sent["scopeContext"]["scope"]
        draft = await workflow.draft(owner, draft_id)
        tone = before["draftDocument"]["reply"]["tone"]
        expected_document = deepcopy(before["draftDocument"])
        expected_document["reply"]["text"] = (
            output("reply_v1", "en", "en")["text"]
            + " Please confirm the separate proposal in writing."
        )
        expected_document["reply"]["generated"][tone] = expected_document["reply"]["text"]
        assert draft["draftDocument"]["reply"]["text"] != before["draftDocument"]["reply"]["text"]
        assert draft["draftDocument"] == expected_document
        assert draft["lastAnalysisRunId"] == before["lastAnalysisRunId"]
        count_before_replay = len(calls)
        replay = await operations.admit(owner, draft_id, "regenerate", regen_command)
        assert replay["operationId"] == regen_ok["operationId"]
        assert not await worker.process_one()
        assert len(calls) == count_before_replay
        assert (await store.get(owner, UUID(regen_ok["operationId"])))[
            "frozen_input"
        ] == frozen_before

        # Late regeneration uses historical scope but cannot overwrite a newer edit.
        regen, _ = await admit("regenerate", draft)
        changed = deepcopy(draft["draftDocument"])
        changed["reply"]["text"] = "New manual reply"
        await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "patch": {"reply.text": "New manual reply"},
            },
        )
        await worker.process_one()
        assert (await operations.status(owner, UUID(regen["operationId"])))["status"] == "failed"
        assert (await workflow.draft(owner, draft_id))["draftDocument"] == changed
        # Drain owned diagnostics; none can write documents or re-dispatch after restart.
        while await worker.process_one(lane="diagnostic"):
            pass
        assert (await workflow.draft(owner, draft_id))["draftDocument"] == changed
        total_calls = len(calls)
        assert not await LlmWorker(factory, store, runner).process_one(lane="diagnostic")
        assert len(calls) == total_calls
        async with database.new_uow() as work:
            diagnostic_rows = (
                (
                    await work.session.execute(
                        text(
                            "SELECT s.accepted_result FROM llm_steps s JOIN llm_operations o "
                            "ON o.id=s.operation_id WHERE o.kind='diagnostic' "
                            "AND s.stage_key LIKE '%_diagnostic'"
                        )
                    )
                )
                .scalars()
                .all()
            )
            observations = [item for row in diagnostic_rows if row for item in row["observations"]]
            assert any(o["outcome"] == "finding" for o in observations)
            assert all(o["rule"] != "semantic_review" for o in observations)
            assert not any(o["outcome"] == "diagnostic_error" for o in observations)
            assert all("candidate.text" not in json.dumps(o) for o in observations)
            assert (
                await work.session.scalar(
                    text(
                        "SELECT count(*) FROM llm_operations WHERE kind='check' AND status='failed'"
                    )
                )
                == 0
            )
        await database.close()

    try:
        asyncio.run(exercise())
    finally:
        engine.dispose()
