"""ANY-663 state/accounting tests exclusively on owned disposable PostgreSQL."""

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.schema_verification import SchemaCompatibilityError
from scope_guard.database.session import Database, normalize_url
from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.gateway import (
    Binding,
    GatewayFailure,
    ProviderRequest,
    ProviderResponse,
)
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.llm.operations import LlmOperations

pytestmark = pytest.mark.integration


def test_durable_idempotency_fencing_and_unknown_cost(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES "
                "('any663@example.test','hash') RETURNING id"
            )
        )
        migrate(connection, target="0005_llm_workflow")

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        store = LlmSQLStore(database.new_uow)
        workflow = WorkflowService(factory)
        project = await workflow.create_project(
            owner,
            {
                "operationId": str(uuid4()),
                "name": "Price monitor",
                "industry": "Development",
                "scope": "DigiKey and Mouser; Arrow and email alerts are excluded.",
                "startDate": "2026-10-01",
                "pricingModel": "hourly",
                "currency": "USD",
                "hourlyRate": "30.00",
                "fixedPrice": None,
            },
        )
        draft = await workflow.project_draft(owner, UUID(project["id"]))
        draft = await workflow.save(
            owner,
            UUID(draft["id"]),
            {
                "operationId": str(uuid4()),
                "expectedRevision": draft["revision"],
                "changes": {"requestText": "Please add Arrow and email alerts."},
            },
        )
        policy = {
            "model": "gpt-5.4-nano",
            "inputRate": "0.000001",
            "outputRate": "0.000002",
            "maxCost": "1.00",
            "maxCalls": 12,
            "durationSeconds": 180,
            "priceSource": "test conservative bound",
            "version": "test-v1",
        }
        operations = LlmOperations(factory, store, policy, language_selector=select)
        command = {
            "operationId": str(uuid4()),
            "expectedRevision": draft["revision"],
            "locale": "ru",
        }
        pending = await operations.admit(owner, UUID(draft["id"]), "check", command)
        repeated = await operations.admit(owner, UUID(draft["id"]), "check", command)
        assert repeated["operationId"] == pending["operationId"]
        with pytest.raises(Exception, match="operationMismatch"):
            await operations.admit(owner, UUID(draft["id"]), "check", {**command, "locale": "en"})
        # Reading does not execute or acquire a lease.
        read = await operations.status(owner, UUID(pending["operationId"]))
        assert read["status"] == "queued"
        claim = await store.claim("test-worker")
        steps = await store.steps(claim["id"])
        binding = Binding(claim["id"], steps[0]["id"], claim["epoch"], policy["model"], "medium")
        request = ProviderRequest(
            binding,
            1,
            [{"role": "user", "content": "frozen request"}],
            {"type": "object"},
            "test",
            60,
        )
        call = await store.reserve(request, 1)
        await store.complete(
            call, response=ProviderResponse("{}", model=policy["model"], provider="openai")
        )
        observed = await store.call(call)
        assert observed["input_tokens"] is None and observed["reported_cost"] is None
        assert observed["estimated_cost"] is None
        assert observed["reserved_cost"] > Decimal(0)
        # Simulated process interruption consumes, rather than resets, the reservation.
        async with database.new_uow() as work:
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET lease_expires_at="
                    "now()-interval '1 second' WHERE id=:id"
                ),
                {"id": claim["id"]},
            )
            await work.commit()
        replacement = await store.claim("replacement")
        assert replacement["epoch"] > claim["epoch"]
        with pytest.raises(GatewayFailure, match="operationLeaseLost"):
            await store.reserve(request, 2)
        assert not await store.renew(claim["id"], claim["epoch"])
        with pytest.raises(Exception, match="analysisNotFound"):
            await operations.status(uuid4(), claim["id"])
        next_binding = Binding(
            replacement["id"], binding.step_id, replacement["epoch"], policy["model"], "medium"
        )
        breached = await store.reserve(
            ProviderRequest(next_binding, 2, request.messages, request.schema, "test", 60), 1
        )
        await store.complete(
            breached, response=ProviderResponse("{}", reported_cost=Decimal(".50"))
        )
        observed = await store.get(owner, claim["id"])
        assert observed["spent"] < Decimal(policy["maxCost"]) and observed["status"] == "failed"
        assert (await store.call(breached))["error"]["code"] == "providerCostBoundExceeded"
        with pytest.raises(GatewayFailure, match="operationLeaseLost"):
            await store.reserve(
                ProviderRequest(next_binding, 3, request.messages, request.schema, "test", 60), 1
            )
        await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_llm_migration_rejects_changed_money_type(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0005_llm_workflow")
        connection.exec_driver_sql(
            "ALTER TABLE provider_calls ALTER COLUMN reported_cost TYPE double precision"
        )
    with pytest.raises(SchemaCompatibilityError):
        with engine.begin() as connection:
            migrate(connection, target="0005_llm_workflow")
    engine.dispose()
