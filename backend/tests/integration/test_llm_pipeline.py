"""Pinned SDKs + controlled provider HTTP + owned PostgreSQL, without a real key."""

import asyncio
import json
from uuid import UUID, uuid4

import httpx
import pytest
from fixtures.llm_ledger import APPROVED
from fixtures.llm_review import labels as document_labels
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

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
    if stage in ("semantic_review_v1", "semantic_review_v2"):
        return APPROVED
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
        "labels": document_labels(language),
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
    "locale,language,wrong,usage,semantic_failure",
    [
        ("ru", "es", 1, True, None),
        ("en", "ru", 0, True, None),
        ("ru", "en", 0, False, None),
        ("ru", "es", 3, True, None),
        ("en", "en", 0, True, "scope"),
        ("en", "en", 0, True, "deadline"),
        ("en", "en", 0, True, "exhaust"),
    ],
)
def test_language_matrix_corrections_accounting_and_historical_regeneration(
    disposable_url,
    locale,
    language,
    wrong,
    usage,
    semantic_failure,
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

        migrate(connection, target="head")

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
        bodies, rejected, semantic_rejected = [], 0, 0
        regeneration_mode, regeneration_attempt = "different", 0

        def http(request):
            nonlocal rejected, regeneration_attempt, semantic_rejected
            body = json.loads(request.content)
            bodies.append(body)
            stage = body["text"]["format"]["name"]
            if stage == "replies_v1" and rejected < wrong:
                rejected += 1
                value = output(stage, locale, "ru")
            else:
                value = output(stage, locale, target)
            bad = (
                "Of course, we can add Arrow and email alerts under the existing agreement "
                "at no extra cost. Send the recipient list and we will get started."
                if semantic_failure == "scope"
                else PROSE["en"] + " We will deliver everything next week."
            )
            if (
                stage == "replies_v1"
                and semantic_failure
                and (semantic_rejected == 0 or semantic_failure == "exhaust")
            ):
                value["warm"] = bad
            if stage == "semantic_review_v1" and semantic_failure:
                payload = json.loads(
                    next(m["content"] for m in body["input"] if m["role"] == "user")
                )
                if payload["candidate"].get("warm") == bad:
                    semantic_rejected += 1
                    value = {
                        "decision": "reject",
                        "violations": [
                            {
                                "field": "warm",
                                "rule": "scope_position"
                                if semantic_failure == "scope"
                                else "timeline_commitment",
                                "feedback": "Remove unauthorized commitments.",
                            }
                        ],
                    }
            if stage == "reply_v1":
                regeneration_attempt += 1
                frozen = json.loads(
                    next(m["content"] for m in body["input"] if m["role"] == "user")
                )
                previous = frozen["previousReply"]["text"]
                if regeneration_mode == "always" or (
                    regeneration_mode in ("once", "whitespace") and regeneration_attempt == 1
                ):
                    value["text"] = (
                        " \n " + previous.replace(" ", "  \n") + " "
                        if regeneration_mode == "whitespace"
                        else previous
                    )
                else:
                    value["text"] = (
                        PROSE[target]
                        if previous != PROSE[target]
                        else {
                            "en": "Before proceeding, please authorize a proposal covering Arrow "
                            "integration and email notifications as extra work.",
                            "ru": "Просим разрешить подготовку предложения по интеграции Arrow "
                            "и почтовым уведомлениям как дополнительным задачам.",
                            "es": "Para continuar, autorice una propuesta que incluya la "
                            "integración de Arrow y las notificaciones por correo como extras.",
                        }[target]
                    )
            if (
                stage == "change_order_v1"
                and "labels" not in body["text"]["format"]["schema"]["properties"]
            ):
                value.pop("labels", None)
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
            assert len(bodies) == 2
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
        # Content findings no longer reject or regenerate a structurally valid candidate.
        assert status["status"] == "succeeded", status
        assert all(c["validation_status"] != "rejected" for c in calls)
        assert status["result"]["draft"]["draftDocument"]["changeOrder"] is None
        assert all(b["text"]["format"]["name"] != "change_order_v1" for b in bodies)
        if not usage:
            assert all(c["input_tokens"] is None and c["estimated_cost"] is None for c in calls)
            assert (await store.get(owner, operation_id))["reserved"] > 0
        assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
        draft = await workflow.draft(owner, draft_id)
        agreement = await operations.admit(
            owner,
            draft_id,
            "agreement",
            {"operationId": str(uuid4()), "expectedRevision": draft["revision"]},
        )
        assert await worker.process_one()
        assert (await operations.status(owner, UUID(agreement["operationId"])))[
            "status"
        ] == "succeeded"
        draft = await workflow.draft(owner, draft_id)
        await workflow.update_project(
            owner,
            UUID(project["id"]),
            {
                **project,
                "scope": "Arrow and email are now included.",
                "hourlyRate": "60.00",
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
            },
        )
        for regeneration_mode in ("different", "once", "whitespace", "always"):
            regeneration_attempt = 0
            before = await workflow.draft(owner, draft_id)
            before_calls = len(bodies)
            command = {"operationId": str(uuid4()), "expectedRevision": before["revision"]}
            pending = await operations.admit(owner, draft_id, "regenerate", command)
            assert await worker.process_one()
            regenerated = await operations.status(owner, UUID(pending["operationId"]))
            assert regenerated["status"] == "succeeded", regenerated
            assert (
                len(bodies) - before_calls
                == {
                    "different": 1,
                    "once": 2,
                    "whitespace": 2,
                    "always": 3,
                }[regeneration_mode]
            )
            assert bodies[-1]["text"]["format"]["name"] == "reply_v1"
            assert "now included" not in json.dumps(bodies[-1]["input"])
            after = await workflow.draft(owner, draft_id)
            assert after["draftDocument"]["changeOrder"] == before["draftDocument"]["changeOrder"]
            assert after["lastAnalysisRunId"] == before["lastAnalysisRunId"]
            for tone in ("warm", "firm"):
                assert (
                    after["draftDocument"]["reply"]["generated"][tone]
                    == before["draftDocument"]["reply"]["generated"][tone]
                )
            if regeneration_mode == "always":
                assert (
                    after["draftDocument"]["reply"]["text"]
                    == before["draftDocument"]["reply"]["text"]
                )
        assert len(await workflow.histories(owner, UUID(project["id"]))) == 1
        # Old queued contracts fail without dispatching or rewriting their frozen input.
        current = await workflow.draft(owner, draft_id)
        old = await operations.admit(
            owner,
            draft_id,
            "check",
            {
                "operationId": str(uuid4()),
                "expectedRevision": current["revision"],
                "locale": locale,
            },
        )
        old_id = UUID(old["operationId"])
        async with database.new_uow() as work:
            await work.session.execute(
                text("UPDATE llm_steps SET prompt_version='workflow-v6' WHERE operation_id=:id"),
                {"id": old_id},
            )
            await work.commit()
        count = len(bodies)
        assert await worker.process_one()
        assert (await operations.status(owner, old_id))["error"][
            "code"
        ] == "errors.workflowVersionUnavailable"
        assert len(bodies) == count
        await adapter.close()
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
