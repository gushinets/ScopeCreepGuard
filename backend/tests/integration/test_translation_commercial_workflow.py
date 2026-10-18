"""Saved terms, bounded repair and atomic publication through the real SQL worker."""

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
from scope_guard.domain.llm.runtime import ProviderResponse
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "scenario,affected",
    [
        ("original", "replies"),
        ("converted", "change_order"),
        ("manual", "replies"),
        ("free", "change_order"),
        ("cleared", "replies"),
        ("exhausted", "change_order"),
        ("late", "replies"),
        ("prose_wrong", "replies"),
        ("prose_repeated", "change_order"),
        ("prose_omitted", "replies"),
    ],
)
def test_translation_saved_authority_correction_and_publication(disposable_url, scenario, affected):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('translation@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="head")
    engine.dispose()

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
                "model": "controlled",
                "inputRate": ".000001",
                "outputRate": ".000002",
                "maxCost": "1",
                "durationSeconds": 180,
            },
            language_selector=select,
        )
        calls, translating = [], False
        entered, release = asyncio.Event(), asyncio.Event()
        fee = {
            "converted": ("220", "EUR"),
            "context_exhausted": ("220", "EUR"),
            "budget": ("220", "EUR"),
            "manual": ("175.35", "USD"),
        }.get(scenario, ("240", "USD"))
        good = "Estos cambios cuestan " + ("175,35" if scenario == "manual" else fee[0])
        good += " " + fee[1] + "."
        if scenario in ("free", "cleared"):
            good = "Estos cambios requieren su aprobación antes de comenzar."

        class Adapter:
            async def request(self, request, timeout):
                calls.append(request)
                stage = request.schema_name.removesuffix("_v1")
                assert request.schema_name != "semantic_review_v2", "No mandatory semantic review"
                value = output(request.schema_name, "en", "es" if translating else "en")
                if not translating and stage == "replies":
                    value.update(
                        dict.fromkeys(("warm", "neutral", "firm"), "These additions cost 240 USD.")
                    )
                if translating:
                    if scenario == "late" and stage == affected:
                        entered.set()
                        await release.wait()
                    payload = json.loads(
                        next(m["content"] for m in request.messages if m["role"] == "user")
                    )
                    expected_terms = {
                        "amount": None if scenario == "cleared" else fee[0],
                        "currency": None if scenario == "cleared" else fee[1],
                        "noAdditionalCharge": scenario == "free",
                    }
                    assert payload["commercialTerms"] == expected_terms
                    assert "hourlyRate" not in payload["project"]
                    assert "currency" not in payload["project"]
                    value["commercialTerms"] = dict(expected_terms)
                    bad = stage == affected and (
                        request.semantic_attempt == 1 or scenario == "exhausted"
                    )
                    if bad and not scenario.startswith("prose_"):
                        value["commercialTerms"].update(amount="999", currency="RUB")
                    elif scenario == "manual":
                        value["commercialTerms"]["amount"] = "175.350"
                    prose = {
                        "prose_wrong": "Estos cambios cuestan 240 euros.",
                        "prose_repeated": "240 USD. 240 USD. 240 USD.",
                        "prose_omitted": "Estos cambios requieren aprobación.",
                    }.get(scenario, good)
                    if stage == "replies":
                        value.update(dict.fromkeys(("warm", "neutral", "firm"), prose))
                    else:
                        value["rationale"] = prose
                        if scenario == "cleared":
                            value.update(description="", timelineImpact="", note="")
                if "labels" not in request.schema.get("properties", {}):
                    value.pop("labels", None)
                return ProviderResponse(json.dumps(value), input_tokens=100, output_tokens=25)

        worker = LlmWorker(
            factory, store, StructuredStageRunner(ProviderGateway(store, Adapter()), store)
        )
        try:
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

            async def save_document(current, document):
                return await workflow.save(
                    owner,
                    draft_id,
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": current["revision"],
                        "changes": {"draftDocument": document},
                    },
                )

            draft = await workflow.save(
                owner,
                draft_id,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": draft["revision"],
                    "changes": {"requestText": "Add Arrow and email alerts."},
                },
            )
            for kind in ("check", "agreement"):
                pending = await operations.admit(
                    owner,
                    draft_id,
                    kind,
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": draft["revision"],
                        **({"locale": "en"} if kind == "check" else {}),
                    },
                )
                await worker.process_one()
                status = await operations.status(owner, UUID(pending["operationId"]))
                assert status["status"] == "succeeded", status
                draft = await workflow.draft(owner, draft_id)
            document = deepcopy(draft["draftDocument"])
            order = document["changeOrder"]
            order.update(
                additionalCost=fee[0],
                currency=fee[1],
                rationale="These additions cost 240 USD.",
                noAdditionalCharge=scenario == "free",
            )
            if scenario == "cleared":
                order.update(
                    additionalCost="",
                    currency="",
                    estimatedHours="",
                    description="",
                    timelineImpact="",
                    note="",
                )
            draft = await save_document(draft, document)
            if scenario == "manual":
                # Later project rates cannot change the meaning of a saved manual fee.
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
            previous = deepcopy(draft)
            command = {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "language": "es",
            }
            pending = await operations.admit(owner, draft_id, "translate", command)
            operation_id = UUID(pending["operationId"])
            frozen = deepcopy((await store.get(owner, operation_id))["frozen_input"])
            assert frozen["currentCommercialTerms"]["additionalCost"] == order["additionalCost"]
            assert frozen["currentCommercialTerms"]["currency"] == order["currency"]
            assert frozen["currentCommercialTerms"]["noAdditionalCharge"] == (scenario == "free")
            calls.clear()
            translating = True
            job = asyncio.create_task(worker.process_one())
            if scenario == "late":
                await asyncio.wait_for(entered.wait(), 30)
                newer = deepcopy(document)
                newer["changeOrder"].update(additionalCost="199", currency="RUB")
                previous = await save_document(draft, newer)
                release.set()
            await job
            status = await operations.status(owner, operation_id)
            saved = await workflow.draft(owner, draft_id)
            if scenario in ("exhausted", "late"):
                assert status["status"] == "failed", status
                assert saved["draftDocument"] == previous["draftDocument"]
                assert saved["revision"] == previous["revision"]
                assert status["error"]["code"] == (
                    "errors.semanticAttemptsExhausted"
                    if scenario == "exhausted"
                    else "errors.draftConflict"
                )
            else:
                assert status["status"] == "succeeded", status
                result = saved["draftDocument"]
                expected_prose = {
                    "prose_wrong": "Estos cambios cuestan 240 euros.",
                    "prose_repeated": "240 USD. 240 USD. 240 USD.",
                    "prose_omitted": "Estos cambios requieren aprobación.",
                }.get(scenario, good)
                assert result["reply"]["text"] == expected_prose
                assert result["changeOrder"]["rationale"] == expected_prose
                assert "commercialTerms" not in result
                assert "commercialTerms" not in result["reply"]
                assert "commercialTerms" not in result["changeOrder"]
                assert (
                    saved["analysisRun"]["resultSnapshot"]
                    == previous["analysisRun"]["resultSnapshot"]
                )
                for field in ("additionalCost", "currency", "estimatedHours", "noAdditionalCharge"):
                    assert result["changeOrder"][field] == order[field]
                if scenario == "cleared":
                    assert (
                        result["changeOrder"]["description"] == result["changeOrder"]["note"] == ""
                    )
            assert all(c.schema_name in ("replies_v1", "change_order_v1") for c in calls)
            assert sum(c.schema_name == affected + "_v1" for c in calls) == (
                1 if scenario.startswith("prose_") else 3 if scenario == "exhausted" else 2
            )
            assert sum(c.schema_name != affected + "_v1" for c in calls) == 1
            assert len(calls) <= 4
            steps = await store.steps(operation_id)
            assert {s["stage_key"] for s in steps} == {"replies", "change_order"}
            assert all("commercialTerms" not in (s["accepted_result"] or {}) for s in steps)
            async with database.new_uow() as work:
                ledger = (
                    (
                        await work.session.execute(
                            text(
                                "SELECT validation_status, input_tokens, output_tokens, "
                                "estimated_cost "
                                "FROM provider_calls WHERE operation_id=:id"
                            ),
                            {"id": operation_id},
                        )
                    )
                    .mappings()
                    .all()
                )
            assert len(ledger) == len(calls)
            assert all(c["input_tokens"] == 100 and c["output_tokens"] == 25 for c in ledger)
            assert all(c["estimated_cost"] > 0 for c in ledger)
            assert sum(c["validation_status"] == "rejected" for c in ledger) == (
                0 if scenario.startswith("prose_") else 3 if scenario == "exhausted" else 1
            )
            if scenario == "prose_wrong":
                # Intentional scope limitation: wrong prose is published, then observed only.
                from scope_guard.domain.llm.runtime import Binding
                from scope_guard.integrations.llm.diagnostics import local_observations

                step = next(s for s in steps if s["stage_key"] == affected)
                observations = local_observations(
                    Binding(operation_id, step["id"], 1, "controlled", "medium"),
                    affected,
                    step["accepted_result"],
                    frozen,
                )
                assert any(
                    o.rule == "commercial_terms" and o.outcome == "finding" for o in observations
                )
                assert (await operations.status(owner, operation_id))["status"] == "succeeded"
                assert (await workflow.draft(owner, draft_id))["draftDocument"] == saved[
                    "draftDocument"
                ]
            before_replay = len(calls)
            if scenario == "original":
                # A completed old-version operation replays its persisted result;
                # it must not reinterpret responses under the new native contract.
                async with database.new_uow() as work:
                    await work.session.execute(
                        text("UPDATE llm_steps SET prompt_version=:version WHERE operation_id=:id"),
                        {"version": "workflow-v9-translation-commercial-terms", "id": operation_id},
                    )
                    await work.commit()
            assert (await operations.admit(owner, draft_id, "translate", command))[
                "operationId"
            ] == str(operation_id)
            assert not await worker.process_one()
            assert len(calls) == before_replay
            assert (await workflow.draft(owner, draft_id))["revision"] == saved["revision"]
            assert (await store.get(owner, operation_id))["frozen_input"] == frozen
        finally:
            await database.close()

    asyncio.run(exercise())
