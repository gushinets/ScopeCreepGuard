"""Final-code regressions through native provider bridge, worker and disposable SQL."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from integration.test_llm_pipeline import REQUESTS, output, provider_response
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.litellm_adapter import LiteLLMResponsesAdapter
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration
D1 = json.loads(
    (Path(__file__).parents[1] / "fixtures/acceptance_d1.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("repeat", range(3))
def test_complete_check_atomic_refresh_and_actual_d1_translation(disposable_url, repeat):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) "
                "VALUES ('acceptance@example.test','hash') RETURNING id"
            )
        )

        migrate(connection, target="head")

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        workflow, store = WorkflowService(factory), LlmSQLStore(database.new_uow)
        policy = {
            "version": "workflow-policy-v1",
            "model": "gpt-5.4-nano",
            "inputRate": ".000001",
            "outputRate": ".000002",
            "maxCost": "1",
            "durationSeconds": 180,
        }
        operations = LlmOperations(factory, store, policy, language_selector=select)
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": f"Acceptance {repeat}",
                "industry": "Development",
                "scope": "Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "endDate": "2026-12-01",
                "pricingModel": "hourly",
                "currency": "USD",
                "hourlyRate": "30.00",
                "fixedPrice": None,
            },
        )
        project_id = UUID(project["id"])
        draft = await workflow.project_draft(owner, project_id)
        draft_id = UUID(draft["id"])

        async def save(document=None, request=None):
            current = await workflow.draft(owner, draft_id)
            changes = {"draftDocument": document} if document else {"requestText": request}
            return await workflow.save(
                owner,
                draft_id,
                {
                    "operationId": str(uuid4()),
                    "expectedRevision": current["revision"],
                    "changes": changes,
                },
            )

        await save(request=REQUESTS["es"])
        wire, co_attempts = [], 0
        mode = "check"

        def http(request):
            nonlocal co_attempts
            body = json.loads(request.content)
            wire.append(body)
            stage = body["text"]["format"]["name"]
            source = json.loads(next(m["content"] for m in body["input"] if m["role"] == "user"))
            facts = source.get("source", source)
            target = facts["selection"]["selectedLanguage"]
            value = output(stage, "en", target)
            if stage == "estimate_v1":
                value.update(additionalCost="640.00", currency="EUR")
            if stage == "change_order_v1":
                value.pop("labels", None)
                if mode == "translate":
                    # Retain the historical prose candidates; content stays diagnostic.
                    value = deepcopy(D1["candidates"][min(co_attempts, 1)])
                    value.pop("labels", None)
                    co_attempts += 1
                    assert "240.00" not in json.dumps(facts["analysis"])
                    assert facts["document"]["changeOrder"]["additionalCost"] == "175.35"
                elif mode == "bad_schedule":
                    value.update(
                        description=D1["saved"]["description"],
                        timelineImpact="3 días naturales después de la aprobación",
                    )
            if facts.get("action") == "translate":
                assert facts["commercialTerms"] == {
                    "amount": "175.35",
                    "currency": "USD",
                    "noAdditionalCharge": True,
                }
                assert "commercialTerms" in body["text"]["format"]["schema"]["properties"]
                value["commercialTerms"] = deepcopy(facts["commercialTerms"])
            return httpx.Response(200, json=provider_response(value, len(wire), True))

        adapter = LiteLLMResponsesAdapter("synthetic", transport=httpx.MockTransport(http))
        worker = LlmWorker(
            factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
        )

        async def operate(kind, **extra):
            current = await workflow.draft(owner, draft_id)
            body = {"operationId": str(uuid4()), "expectedRevision": current["revision"], **extra}
            pending = await operations.admit(owner, draft_id, kind, body)
            assert await worker.process_one()
            status = await operations.status(owner, UUID(pending["operationId"]))
            count = len(wire)
            assert (await operations.admit(owner, draft_id, kind, body))["operationId"] == pending[
                "operationId"
            ]
            assert len(wire) == count
            return status

        checked = await operate("check", locale="en")
        assert checked["status"] == "succeeded", checked["error"]
        assert len(wire) == 2
        assert (await operate("agreement"))["status"] == "succeeded"
        baseline = (await workflow.draft(owner, draft_id))["draftDocument"]
        assert baseline["changeOrder"]["changeOrderLabels"]
        assert len(await workflow.histories(owner, project_id)) == 1
        # Price changes are explicit current-project input, scope remains historical.
        await workflow.update_project(
            owner,
            project_id,
            {
                **project,
                "operationId": str(uuid4()),
                "expectedRevision": (await workflow.draft(owner, draft_id))["revision"],
                "currency": "EUR",
                "hourlyRate": "80.00",
                "scope": "Arrow and email alerts are now included.",
            },
        )
        for edits in (
            {},
            {"additionalCost": "175.35", "currency": "USD"},
            {"currency": "RUB"},
            {"additionalCost": "175.35", "currency": "RUB"},
            {"additionalCost": "175.35", "estimatedHours": "2.5"},
            {"noAdditionalCharge": True},
        ):
            document = deepcopy((await workflow.draft(owner, draft_id))["draftDocument"])
            if not edits:
                document["changeOrder"].update(
                    {
                        field: value
                        for field, value in document["changeOrder"]["aiValues"].items()
                        if not field.startswith("manual")
                    }
                )
                document["changeOrder"]["noAdditionalCharge"] = False
            document["changeOrder"].update(edits)
            await save(document=document)
            previous = deepcopy(document["changeOrder"])
            refreshed = await operate("estimate")
            assert refreshed["status"] == "succeeded", refreshed["error"]
            reloaded = (await workflow.draft(owner, draft_id))["draftDocument"]["changeOrder"]
            if edits:
                assert (reloaded["additionalCost"], reloaded["currency"]) == (
                    previous["additionalCost"],
                    previous["currency"],
                )
                assert reloaded["rationale"] == ""
            else:
                assert (reloaded["additionalCost"], reloaded["currency"]) == ("640.00", "EUR")
            if "estimatedHours" in edits:
                assert reloaded["estimatedHours"] == "2.5"
            assert reloaded["aiValues"]["additionalCost"] == "640.00"
            assert reloaded["aiValues"]["currency"] == "EUR"
            assert len(await workflow.histories(owner, project_id)) == 1

        document = deepcopy((await workflow.draft(owner, draft_id))["draftDocument"])
        document["changeOrder"].update(
            D1["saved"],
            providerName="Diseño Muñoz Álvarez",
            clientName="Clínica Peña",
            estimatedHours="2.5",
            additionalCost="175.35",
            currency="USD",
        )
        await save(document=document)
        mode = "translate"
        calls_before_translation = len(wire)
        translated = await operate("translate", language="en")
        assert translated["status"] == "succeeded", translated["error"]
        assert len(wire) == calls_before_translation + 2
        reloaded = await workflow.draft(owner, draft_id)
        order = reloaded["draftDocument"]["changeOrder"]
        assert (order["additionalCost"], order["currency"], order["estimatedHours"]) == (
            "175.35",
            "USD",
            "2.5",
        )
        assert order["description"] == D1["candidates"][0]["description"]
        assert order["timelineImpact"] == D1["candidates"][0]["timelineImpact"]
        assert co_attempts == 1
        assert order["noAdditionalCharge"] is True
        assert len(await workflow.histories(owner, project_id)) == 1
        before = deepcopy(reloaded)
        mode = "bad_schedule"
        calls_before_translation = len(wire)
        rejected = await operate("translate", language="es")
        assert rejected["status"] == "succeeded"
        assert len(wire) == calls_before_translation + 2
        assert (await workflow.draft(owner, draft_id))["draftDocument"]["changeOrder"][
            "timelineImpact"
        ] == "3 días naturales después de la aprobación"
        assert (
            int((await workflow.draft(owner, draft_id))["revision"]) == int(before["revision"]) + 1
        )
        assert rejected["error"] is None
        await adapter.close()
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
