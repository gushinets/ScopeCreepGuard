"""Pinned SDKs + controlled provider HTTP + owned PostgreSQL, without a real key."""

import asyncio
import json
from decimal import Decimal
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
from scope_guard.domain.llm.runtime import PROMPT_VERSION
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
    if stage == "semantic_review_v1":
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
                previous = frozen["document"]["reply"]["text"]
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
                        else PROSE[target]
                        + " "
                        + {
                            "en": "Please confirm whether to prepare that proposal for review.",
                            "ru": "Подтвердите, пожалуйста, необходимость подготовки "
                            "отдельного предложения.",
                            "es": "Confirme si debemos preparar esa propuesta para su revisión.",
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
            assert len(bodies) == 5
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
        if wrong == 3 or semantic_failure == "exhaust":
            assert status["status"] == "failed" and status["result"] is None
            assert status["error"]["code"] == "errors.semanticAttemptsExhausted"
            assert status["stages"]["analysis"] == "accepted"
            assert not await workflow.histories(owner, UUID(project["id"]))
        else:
            assert status["status"] == "succeeded", (
                status["error"],
                [(s["stage_key"], s["feedback"]) for s in await store.steps(operation_id)],
            )
            assert len(bodies) == 5 + wrong + int(interrupted) + (2 if semantic_failure else 0)
            if semantic_failure:
                assert semantic_rejected == 1
                assert sum(c["validation_status"] == "rejected" for c in calls) == 1
                assert all(c["estimated_cost"] is not None for c in calls)
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
            # Only the reply stage retries; failed replacements retain the saved Draft.
            for regeneration_mode in ("once", "whitespace", "always"):
                regeneration_attempt = 0
                if regeneration_mode == "always":
                    edited = await workflow.draft(owner, draft_id)
                    manual = edited["draftDocument"]
                    manual["reply"]["text"] += (
                        " "
                        + {
                            "en": "Please preserve our manually agreed recipient list.",
                            "ru": "Пожалуйста, сохраните согласованный вручную список получателей.",
                            "es": "Conserve nuestra lista de destinatarios acordada manualmente.",
                        }[target]
                    )
                    manual["changeOrder"].update(
                        additionalCost="333.00", estimatedHours="9.5", currency="EUR"
                    )
                    await workflow.save(
                        owner,
                        draft_id,
                        {
                            "operationId": str(uuid4()),
                            "expectedRevision": edited["revision"],
                            "changes": {"draftDocument": manual},
                        },
                    )
                before = await workflow.draft(owner, draft_id)
                before_history = len(await workflow.histories(owner, UUID(project["id"])))
                before_calls = len(bodies)
                pending = await operations.admit(
                    owner,
                    draft_id,
                    "regenerate",
                    {"operationId": str(uuid4()), "expectedRevision": before["revision"]},
                )
                regenerate_id = UUID(pending["operationId"])
                assert await worker.process_one()
                regenerated = await operations.status(owner, regenerate_id)
                expected_calls = 3
                assert len(bodies) - before_calls == expected_calls
                assert all(
                    b["text"]["format"]["name"] in ("reply_v1", "semantic_review_v1")
                    for b in bodies[before_calls:]
                )
                async with database.new_uow() as work:
                    attempts = (
                        (
                            await work.session.execute(
                                text(
                                    "SELECT * FROM provider_calls WHERE operation_id=:id "
                                    "ORDER BY physical_index"
                                ),
                                {"id": regenerate_id},
                            )
                        )
                        .mappings()
                        .all()
                    )
                assert len(attempts) == expected_calls
                assert all(
                    c["validation_status"] == "rejected"
                    for c in attempts[: expected_calls if regeneration_mode == "always" else 1]
                )
                assert all(c["reported_cost"] is None for c in attempts)
                assert all((c["estimated_cost"] is not None) == usage for c in attempts)
                after = await workflow.draft(owner, draft_id)
                assert (
                    after["draftDocument"]["changeOrder"] == before["draftDocument"]["changeOrder"]
                )
                assert after["lastAnalysisRunId"] == before["lastAnalysisRunId"]
                assert len(await workflow.histories(owner, UUID(project["id"]))) == before_history
                if regeneration_mode == "always":
                    assert regenerated["status"] == "failed"
                    assert regenerated["error"]["code"] == "errors.semanticAttemptsExhausted"
                    assert "unchanged_reply" in json.dumps(regenerated["error"])
                    assert after["draftDocument"] == before["draftDocument"]
                    assert after["revision"] == before["revision"]
                else:
                    assert regenerated["status"] == "succeeded"
                    assert (
                        after["draftDocument"]["reply"]["text"]
                        != before["draftDocument"]["reply"]["text"]
                    )
            regeneration_mode = "different"
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
            # Old pending work must not resume under changed prompts or consume calls.
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
            assert all(s["prompt_version"] == PROMPT_VERSION for s in await store.steps(old_id))
            async with database.new_uow() as work:
                await work.session.execute(
                    text(
                        "UPDATE llm_steps SET prompt_version='workflow-v3' WHERE operation_id=:id"
                    ),
                    {"id": old_id},
                )
                await work.commit()
            count = len(bodies)
            assert await worker.process_one()
            old_status = await operations.status(owner, old_id)
            assert old_status["error"]["code"] == "errors.workflowVersionUnavailable"
            assert len(bodies) == count
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
