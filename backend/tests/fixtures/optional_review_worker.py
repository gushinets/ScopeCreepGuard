"""Test-only production composition injection; blocks every non-PostgreSQL socket."""

import asyncio
import importlib.util
import json
import socket
import sys
from uuid import UUID, uuid4

# Resolve only the isolated Compose database, then fail closed on other connections.
allowed_ips = {item[4][0] for item in socket.getaddrinfo("postgres", 5432)}


def network_guard(event, args):
    if event == "socket.connect":
        address = args[1]
        if not isinstance(address, tuple) or address[0] not in allowed_ips or address[1] != 5432:
            raise RuntimeError("Test contour forbids non-PostgreSQL connections")


sys.addaudithook(network_guard)

from sqlalchemy import text  # noqa: E402

from scope_guard.core.config import Settings  # noqa: E402
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork  # noqa: E402
from scope_guard.database.session import create_database  # noqa: E402
from scope_guard.domain.llm.runtime import ProviderResponse  # noqa: E402
from scope_guard.integrations.llm import litellm_adapter  # noqa: E402
from scope_guard.integrations.llm.detection import select  # noqa: E402
from scope_guard.services.drafts.workflow import WorkflowService  # noqa: E402
from scope_guard.services.llm import worker as worker_module  # noqa: E402
from scope_guard.services.llm.operations import LlmOperations  # noqa: E402


async def main():
    settings = Settings()
    database = create_database(settings)
    calls = []
    async with database.engine.begin() as connection:
        owner = await connection.scalar(
            text("INSERT INTO users(email,password_hash) VALUES (:email,'hash') RETURNING id"),
            {"email": uuid4().hex + "@example.test"},
        )
        await connection.execute(
            text("INSERT INTO profiles(user_id) VALUES (:owner)"), {"owner": owner}
        )

    def factory():
        return WorkflowUnitOfWork(database.new_uow())

    workflow = WorkflowService(factory)
    project = await workflow.create_project(
        owner,
        {
            "operationId": str(uuid4()),
            "name": "Diagnostic component fixture",
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
    # The fixture creates a primary operation; real main composes both execution lanes.
    from scope_guard.database.repositories.llm import LlmSQLStore

    operations = LlmOperations(
        factory,
        LlmSQLStore(database.new_uow),
        {
            "version": "workflow-policy-v1",
            "model": settings.openai_model,
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

    class ControlledAdapter:
        async def request(self, request, timeout):
            calls.append(request.schema_name)
            if request.schema_name == "semantic_review_v2":
                value = {"decision": "accept", "violations": []}
            elif request.schema_name == "analysis_v1":
                value = {
                    "verdict": "out_of_scope",
                    "confidence": 95,
                    "summary": "The client asks for additional work.",
                    "reasoning": "Arrow and email alerts are excluded.",
                    "citations": ["Arrow and email alerts are excluded."],
                    "suggestion": "Prepare a separate estimate.",
                    "hasAdditionalWork": True,
                    "estimatedHours": 8,
                    "additionalCost": "240.00",
                    "currency": "USD",
                }
            else:
                assert request.schema_name == "replies_v1"
                value = {
                    "scopePosition": "out_of_scope",
                    **dict.fromkeys(
                        ("warm", "neutral", "firm"),
                        "These additions require a separate estimate and approval.",
                    ),
                }
            return ProviderResponse(
                json.dumps(value), model="controlled-actual", input_tokens=100, output_tokens=25
            )

        async def close(self):
            pass

    class ObservedWorker(worker_module.LlmWorker):
        async def execute(self, operation):
            await super().execute(operation)
            if operation["kind"] == "diagnostic":
                self.stopping.set()

    litellm_adapter.LiteLLMResponsesAdapter = lambda key: ControlledAdapter()
    worker_module.LlmWorker = ObservedWorker
    spec = importlib.util.spec_from_file_location("production_worker", "/app/export_worker.py")
    composition = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composition)
    await asyncio.wait_for(composition.main(), 120)
    parent = await operations.status(owner, UUID(pending["operationId"]))
    assert parent["status"] == "succeeded", parent
    async with database.engine.connect() as connection:
        job = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM llm_operations WHERE kind='diagnostic' AND owner_id=:owner"
                    ),
                    {"owner": owner},
                )
            )
            .mappings()
            .one()
        )
    assert job["status"] == "succeeded", job
    review = next(r for r in job["result"]["reviews"] if r["stage"] == "replies")
    want = "completed_clean" if settings.llm_semantic_review_enabled else "skipped_disabled"
    assert review["outcome"] == want, review
    assert calls.count("semantic_review_v2") == int(settings.llm_semantic_review_enabled)
    assert calls[:2] == ["analysis_v1", "replies_v1"]
    print(
        json.dumps(
            {
                "enabled": settings.llm_semantic_review_enabled,
                "calls": calls,
                "outcome": review["outcome"],
                "network": "PostgreSQL only; non-database socket.connect denied",
            }
        )
    )
    await database.close()


asyncio.run(main())
