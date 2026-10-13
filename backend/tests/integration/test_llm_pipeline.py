"""Pinned SDKs + controlled provider HTTP + owned PostgreSQL, without a real key."""

import asyncio
import json
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.change_orders.constants import LABEL_KEYS
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.litellm_adapter import LiteLLMResponsesAdapter
from scope_guard.integrations.llm.stages import StructuredStageRunner
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations
from scope_guard.services.llm.worker import LlmWorker

pytestmark = pytest.mark.integration

REQUESTS = {
    "en": "Please add Arrow as a third supplier and send price alerts by email as well.",
    "ru": "Добавьте поставщика Arrow и уведомления о новых ценах по электронной почте.",
    "es": "¿Podéis añadir el proveedor Arrow y enviar avisos de nuevos precios "
    "por correo electrónico?",
}
PROSE = {
    "en": "These additions are outside the agreed scope and require a separate estimate "
    "and approval.",
    "ru": "Эти изменения выходят за рамки согласованного объёма работ "
    "и требуют отдельной оценки и согласования.",
    "es": "Estos cambios están fuera del alcance acordado y requieren una estimación "
    "independiente y aprobación.",
}


def output(stage, locale, language):
    if stage == "analysis_v1":
        return {
            "verdict": "out_of_scope",
            "confidence": 95,
            "summary": PROSE[locale],
            "reasoning": PROSE[locale],
            "suggestion": PROSE[locale],
            "citations": ["Arrow and email alerts are excluded."],
            "hasAdditionalWork": True,
            "estimatedHours": 8,
            "additionalCost": "240.00",
            "currency": "USD",
        }
    if stage == "replies_v1":
        return {
            "scopePosition": "out_of_scope",
            **dict.fromkeys(("warm", "neutral", "firm"), PROSE[language]),
        }
    if stage == "reply_v1":
        return {"scopePosition": "out_of_scope", "text": PROSE[language]}
    if stage == "estimate_v1":
        return {
            "scopePosition": "out_of_scope",
            "estimatedHours": 8,
            "additionalCost": "480.00",
            "currency": "USD",
            "rationale": PROSE[language],
        }
    return {
        "scopePosition": "out_of_scope",
        "applicable": True,
        **dict.fromkeys(("description", "timelineImpact", "rationale", "note"), PROSE[language]),
        "additionalTerms": "",
        "labels": dict.fromkeys(LABEL_KEYS, PROSE[language]),
    }


def provider_response(payload, index, usage):
    return {
        "id": f"resp_{index}",
        "object": "response",
        "created_at": 1,
        "model": "gpt-5.4-nano",
        "status": "completed",
        "output": [
            {
                "id": f"msg_{index}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(payload, ensure_ascii=False),
                        "annotations": [],
                    }
                ],
            }
        ],
        **(
            {"usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125}}
            if usage
            else {}
        ),
    }


@pytest.mark.parametrize(
    "locale,language,wrong,usage",
    [
        ("ru", "es", 1, True),
        ("en", "ru", 0, True),
        ("ru", "en", 0, False),
        ("ru", "es", 3, True),
    ],
)
def test_language_matrix_corrections_accounting_and_historical_regeneration(
    disposable_url,
    locale,
    language,
    wrong,
    usage,
):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('pipeline@example.test','hash') RETURNING id"
            )
        )

    async def exercise():
        target = language
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
                "name": "Monitor",
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
        draft = await workflow.project_draft(owner, UUID(project["id"]))
        draft_id = UUID(draft["id"])
        draft = await workflow.save(
            owner,
            draft_id,
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"requestText": REQUESTS[language]},
            },
        )
        bodies, rejected = [], 0

        def http(request):
            nonlocal rejected
            body = json.loads(request.content)
            bodies.append(body)
            stage = body["text"]["format"]["name"]
            if stage == "replies_v1" and rejected < wrong:
                rejected += 1
                value = output(stage, locale, "ru")
            else:
                value = output(stage, locale, target)
            return httpx.Response(200, json=provider_response(value, len(bodies), usage))

        adapter = LiteLLMResponsesAdapter("synthetic", transport=httpx.MockTransport(http))
        interrupt = locale == "ru" and language == "en"
        dispatched = asyncio.Event()

        async def interruptible_http(request):
            nonlocal interrupt
            if interrupt:
                interrupt = False
                bodies.append(json.loads(request.content))
                dispatched.set()
                await asyncio.Event().wait()
            return http(request)

        if interrupt:
            await adapter.close()
            adapter = LiteLLMResponsesAdapter(
                "synthetic", transport=httpx.MockTransport(interruptible_http)
            )
        fault = locale == "en" and language == "ru"

        class PublicationUoW(WorkflowUnitOfWork):
            async def __aenter__(self):
                work = await super().__aenter__()
                publish = work.llm.publish

                async def rollback_publication(*args):
                    nonlocal fault
                    await publish(*args)
                    if fault:
                        fault = False
                        raise OperationalError(
                            "synthetic publication failure", {}, RuntimeError("synthetic")
                        )

                work.llm.publish = rollback_publication
                return work

        def publication_factory():
            return PublicationUoW(database.new_uow())

        worker = LlmWorker(
            publication_factory,
            store,
            StructuredStageRunner(ProviderGateway(store, adapter), store),
        )
        pending = await operations.admit(
            owner,
            draft_id,
            "check",
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "locale": locale,
                **({"documentLanguage": "en"} if locale == "ru" and language == "en" else {}),
            },
        )
        interrupted = locale == "ru" and language == "en"
        if interrupted:
            running = asyncio.create_task(worker.process_one())
            await asyncio.wait_for(dispatched.wait(), timeout=30)
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
            worker = LlmWorker(
                factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
            )
        if fault:
            assert not await worker.process_one()
            assert len(bodies) == 3
            assert not await workflow.histories(owner, UUID(project["id"]))
            worker = LlmWorker(
                factory, store, StructuredStageRunner(ProviderGateway(store, adapter), store)
            )
        assert await worker.process_one()
        operation_id = UUID(pending["operationId"])
        status = await operations.status(owner, operation_id)
        assert status["stages"]["analysis"] == "accepted", (
            [(s["stage_key"], s["feedback"]) for s in await store.steps(operation_id)],
            [b["text"]["format"]["name"] for b in bodies],
        )
        async with database.new_uow() as work:
            calls = (
                (
                    await work.session.execute(
                        text("SELECT * FROM provider_calls WHERE operation_id=:id"),
                        {"id": operation_id},
                    )
                )
                .mappings()
                .all()
            )
        assert len(calls) == len(bodies)
        assert all(c["reported_cost"] is None for c in calls)
        if wrong == 1:
            assert sum(c["validation_status"] == "rejected" for c in calls) == 1
            assert all(c["estimated_cost"] is not None for c in calls)
        if not usage:
            assert all(c["input_tokens"] is None and c["estimated_cost"] is None for c in calls)
            assert (await store.get(owner, operation_id))["reserved"] > Decimal(0)
        if wrong == 3:
            assert status["status"] == "failed" and status["result"] is None
            assert status["error"]["code"] == "errors.semanticAttemptsExhausted"
            assert status["stages"]["analysis"] == "accepted"
            assert not await workflow.histories(owner, UUID(project["id"]))
        else:
            assert status["status"] == "succeeded", (
                status["error"],
                [(s["stage_key"], s["feedback"]) for s in await store.steps(operation_id)],
            )
            assert len(bodies) == 3 + wrong + int(interrupted)
            result = status["result"]["analysisRun"]["resultSnapshot"]
            assert (
                result["summary"] == PROSE[locale]
                and result["replies"]["neutral"] == PROSE[language]
            )
            draft = await workflow.draft(owner, draft_id)
            assert draft["draftDocument"]["reply"]["language"] == language
            assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
            # Change the current scope; regenerations must retain this check's historical scope.
            await workflow.update_project(
                owner,
                UUID(project["id"]),
                {
                    **project,
                    "scope": "Arrow and email alerts are now included.",
                    "hourlyRate": "60.00",
                    "operationId": str(uuid4()),
                    "expectedRevision": draft["revision"],
                },
            )
            for _ in range(2):
                draft = await workflow.draft(owner, draft_id)
                pending = await operations.admit(
                    owner,
                    draft_id,
                    "regenerate",
                    {"operationId": str(uuid4()), "expectedRevision": draft["revision"]},
                )
                assert await worker.process_one()
                assert (await operations.status(owner, UUID(pending["operationId"])))[
                    "status"
                ] == "succeeded"
                assert "now included" not in json.dumps(bodies[-1]["input"])
            if locale == "en" and language == "ru":
                draft = await workflow.draft(owner, draft_id)
                pending = await operations.admit(
                    owner,
                    draft_id,
                    "estimate",
                    {"operationId": str(uuid4()), "expectedRevision": draft["revision"]},
                )
                frozen = (await store.get(owner, UUID(pending["operationId"])))["frozen_input"]
                assert frozen["project"]["hourlyRate"] == "60.00"
                assert frozen["project"]["scope"] == "Arrow and email alerts are excluded."
                assert await worker.process_one()
                estimate = await operations.status(owner, UUID(pending["operationId"]))
                assert estimate["status"] == "succeeded", estimate["error"]
                assert estimate["result"]["analysisRun"]["purpose"] == "estimate"
                assert (
                    estimate["result"]["analysisRun"]["resultSnapshot"]["changeOrder"][
                        "additionalCost"
                    ]
                    == "480.00"
                )
                assert (await workflow.draft(owner, draft_id))["lastAnalysisRunId"] == draft[
                    "lastAnalysisRunId"
                ]
            assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
            if locale == "ru" and language == "en":
                # Translation remains this check, with the same manual commercial values.
                draft = await workflow.draft(owner, draft_id)
                document = draft["draftDocument"]
                document["reply"]["text"] = PROSE["en"] + " Please review the proposal carefully."
                document["changeOrder"].update(
                    additionalCost="333.00",
                    estimatedHours="9.5",
                    currency="EUR",
                    endDate="2027-01-01",
                )
                draft = await workflow.save(
                    owner,
                    draft_id,
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": draft["revision"],
                        "changes": {"draftDocument": document},
                    },
                )
                target = "es"
                pending = await operations.admit(
                    owner,
                    draft_id,
                    "translate",
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": draft["revision"],
                        "language": target,
                    },
                )
                assert await worker.process_one()
                translated = await operations.status(owner, UUID(pending["operationId"]))
                assert translated["status"] == "succeeded", translated["error"]
                reopened = await workflow.draft(owner, draft_id)
                co = reopened["draftDocument"]["changeOrder"]
                assert (
                    co["additionalCost"],
                    co["estimatedHours"],
                    co["currency"],
                    co["endDate"],
                ) == ("333.00", "9.5", "EUR", "2027-01-01")
                assert reopened["analysisRun"]["resultSnapshot"] == result
                assert reopened["draftDocument"]["languageSelection"]["override"] is True
                assert reopened["draftDocument"]["reply"]["language"] == "es"
                assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
                # New request clears the override; prior materials never enter a new check.
                reopened = await workflow.save(
                    owner,
                    draft_id,
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": reopened["revision"],
                        "changes": {"requestText": REQUESTS["ru"]},
                    },
                )
                assert reopened["draftDocument"]["languageSelection"]["override"] is False
                pending = await operations.admit(
                    owner,
                    draft_id,
                    "check",
                    {
                        "operationId": str(uuid4()),
                        "expectedRevision": reopened["revision"],
                        "locale": "ru",
                    },
                )
                frozen = (await store.get(owner, UUID(pending["operationId"])))["frozen_input"]
                assert frozen["selection"]["selectedLanguage"] == "ru"
                assert (
                    frozen["document"]["reply"]["text"] == ""
                    and frozen["document"]["changeOrder"] is None
                )
                history = (await workflow.histories(owner, UUID(project["id"])))[0]
                restored = await workflow.reopen_history(
                    owner,
                    UUID(history["id"]),
                    {"operationId": str(uuid4()), "expectedRevision": reopened["revision"]},
                )
                assert restored["draftDocument"]["languageSelection"]["override"] is True
                assert restored["draftDocument"]["reply"]["language"] == "en"
        await adapter.close()
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
