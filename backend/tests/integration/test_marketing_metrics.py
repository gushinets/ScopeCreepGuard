"""Reconciliation owns only disposable PostgreSQL; fixtures never target app settings."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.marketing import LOCK_KEY
from scope_guard.database.repositories.users import Users
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.services.drafts.workflow import WorkflowService
from scope_guard.services.marketing.service import MetricsService

pytestmark = pytest.mark.integration


def prepare(url, target="head"):
    engine = create_engine(normalize_url(url))
    with engine.begin() as connection:
        migrate(connection, target=target)
    engine.dispose()


async def seed(database, when, *, excluded=False):
    async with database.new_uow() as work:
        owner = await Users(work.session).insert(f"{uuid4()}@example.test", "synthetic")
        await work.session.execute(
            text(
                "UPDATE profiles SET created_at=:stamp,analytics_excluded=:excluded "
                "WHERE user_id=:owner"
            ),
            {"stamp": when - timedelta(days=1), "excluded": excluded, "owner": owner.id},
        )
        await work.commit()
    workflow = WorkflowService(lambda: WorkflowUnitOfWork(database.new_uow()))
    project = await workflow.create_project(
        owner.id,
        {
            "operationId": str(uuid4()),
            "name": "Metrics fixture",
            "industry": "Development",
            "startDate": when.date().isoformat(),
            "scope": "Original agreed work",
            "currency": "USD",
            "pricingModel": "hourly",
            "hourlyRate": "30.00",
            "fixedPrice": None,
        },
    )
    draft = await workflow.project_draft(owner.id, UUID(project["id"]))
    return {"owner": owner.id, "project": project["id"], "draft": draft["id"], "stamp": when}


async def saved_check(database, values, *, run=None, purpose="check"):
    values = {**values, "run": run or uuid4(), "key": uuid4()}
    async with database.new_uow() as work:
        await work.session.execute(
            text("""
        INSERT INTO analysis_runs(id,project_id,source_draft_id,source_draft_revision,
         requested_by_user_id,request_text,project_snapshot,interface_locale,input_schema_version,
         status,result_snapshot,result_schema_version,idempotency_key,request_hash,created_at,finished_at)
        VALUES(:run,:project,:draft,1,:owner,'request','{}','en',1,'succeeded','{}',1,
         :key,'fixture',:stamp-interval '2 seconds',:stamp) ON CONFLICT(id) DO NOTHING
        """),
            values,
        )
        history = await work.session.scalar(
            text("""
        INSERT INTO history_entries(project_id,date,request,verdict,summary,source_draft_id,
         source_draft_revision,analysis_run_id,check_snapshot,schema_version,completed_at,
         saved_by_user_id,source_kind,idempotency_key,request_hash)
        VALUES(:project,CAST(:stamp AS date),'request','out_of_scope','summary',:draft,1,
         :run,'{}',2,:stamp,:owner,'explicit',:key,'fixture') RETURNING id
        """),
            values,
        )
        if purpose == "estimate":
            await work.session.execute(
                text("""
            INSERT INTO activity_events(project_id,analysis_run_id,actor_type,actor_user_id,
             event_type,operation_id,payload,payload_version)
            VALUES(:project,:run,'user',:owner,'analysis_created',:key,
             jsonb_build_object('purpose','estimate'),1)
            """),
                values,
            )
        # Simulates interruption after source commit: no dirty event or callback.
        await work.commit()
    return values["run"], history


def test_full_recovery_late_facts_feedback_exclusions_and_repeat(disposable_url):
    prepare(disposable_url)

    async def exercise():
        database = Database(normalize_url(disposable_url))
        day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=2
        )
        owner = await seed(database, day)
        excluded = await seed(database, day, excluded=True)
        runs = []
        for _ in range(3):
            runs.append(await saved_check(database, owner))
        await saved_check(database, owner, run=runs[0][0])  # second archive of same run
        await saved_check(database, owner, purpose="estimate")
        await saved_check(database, excluded)
        async with database.new_uow() as work:
            await work.session.execute(
                text("""
            INSERT INTO change_orders(project_id,history_entry_id,reference,content_snapshot,
             schema_version,status,revision,finalized_by_user_id,idempotency_key,request_hash,
             finalized_at,voided_at) VALUES(:project,:history,:reference,'{}',1,'voided',2,
             :owner,:key,'fixture',:stamp,:stamp+interval '1 day')
            """),
                {**owner, "history": runs[0][1], "reference": str(uuid4()), "key": uuid4()},
            )
            await work.commit()
        await database.close()
        # New process context repairs source commits without replaying generators.
        database = Database(normalize_url(disposable_url))
        metrics = MetricsService(database.new_metrics_uow)
        rows = await metrics.read(day.date(), day.date() + timedelta(days=2))
        assert len(rows) == 2
        row = rows[0]
        assert row["dau"] == row["mau"] == row["pql_profiles"] == 1
        assert row["check_succeeded"] == 3 and row["estimate_succeeded"] == 1
        assert row["analysis_adoption_percent"] == 100
        assert row["change_orders_created"] == 1 and rows[1]["change_orders_voided"] == 1
        assert row["registered_profiles"] == 1
        async with database.new_uow() as work:
            await work.session.execute(
                text("""
            INSERT INTO evaluation_cases(user_id,analysis_run_id,scope,request,ai_verdict,
             ai_reasoning,accuracy,industry,human_verdict)
             VALUES(:owner,:run,'scope','request','out_of_scope',
             'reason','correct','Development','out_of_scope')
            """),
                {**owner, "run": runs[0][0]},
            )
            await work.commit()
        row = (await metrics.read(day.date(), day.date() + timedelta(days=1)))[0]
        assert row["verdict_correct"] == row["verdict_evaluated_checks"] == 1
        async with database.new_uow() as work:
            await work.session.execute(
                text("UPDATE evaluation_cases SET accuracy='wrong',human_verdict='in_scope'")
            )
            await work.commit()
        changed = (await metrics.read(day.date(), day.date() + timedelta(days=1)))[0]
        assert changed["verdict_correct"] == 0 and changed["verdict_wrong"] == 1
        repeated = (await metrics.reconcile(day.date(), day.date() + timedelta(days=1)))[0]
        assert {k: v for k, v in changed.items() if k not in ("calculated_at", "data_through")} == {
            k: v for k, v in repeated.items() if k not in ("calculated_at", "data_through")
        }
        # Late midnight completion lands on its saved day, not reconciliation day.
        await saved_check(database, {**owner, "stamp": day + timedelta(days=1)})
        late = await metrics.read(day.date(), day.date() + timedelta(days=2))
        assert late[0]["check_succeeded"] == 3 and late[1]["check_succeeded"] == 1
        async with database.new_uow() as work:
            await work.session.execute(text("UPDATE profiles SET analytics_excluded=true"))
            await work.commit()
        cleared = await metrics.read(day.date(), day.date() + timedelta(days=2))
        assert all(
            r["dau"] == r["registered_profiles"] == r["check_succeeded"] == 0 for r in cleared
        )
        await database.close()

    asyncio.run(exercise())


def test_t2_failure_keeps_authenticated_api_result_and_rollback_is_atomic(
    disposable_url, monkeypatch, caplog
):
    import httpx
    from pydantic import SecretStr
    from scope_guard_api.main import create_app

    from scope_guard.core.config import Settings

    prepare(disposable_url)

    async def fail(self):
        assert self.engine.pool.checkedout() == 0
        raise RuntimeError("forced T2 failure")

    async def exercise():
        monkeypatch.setattr(Database, "_reconcile_metrics", fail)
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("metrics-test"),
                workflow_v2=True,
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/register",
                    json={"email": "metrics@example.test", "password": "synthetic-password"},
                )
                assert response.status_code == 201, response.text
                assert (await client.get("/api/v2/profile")).status_code == 200
                async with app.state.database.new_uow() as work:
                    await Users(work.session).insert("rollback@example.test", "synthetic")
                    # no commit: profile, revision and event must roll back with user
                async with app.state.database.new_uow() as work:
                    for table in ("users", "profiles", "profile_revisions", "activity_events"):
                        assert await work.session.scalar(text(f"SELECT count(*) FROM {table}")) == 1
                    assert (
                        await work.session.scalar(text("SELECT count(*) FROM marketing_metrics"))
                        == 0
                    )
        assert "marketing_metrics_reconciliation_failed" in caplog.text
        database = Database(normalize_url(disposable_url))
        today = datetime.now(UTC).date()
        rows = await MetricsService(database.new_metrics_uow).read(today, today + timedelta(days=1))
        assert rows[0]["registered_profiles"] == 1 and rows[0]["dau"] == 0
        await database.close()

    asyncio.run(exercise())


def test_waiting_reconciliation_takes_snapshot_after_lock_and_preserves_freshness(disposable_url):
    prepare(disposable_url)

    async def exercise():
        database = Database(normalize_url(disposable_url))
        today = datetime.now(UTC).date()
        async with database.new_uow() as blocking:
            await blocking.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY}
            )
            waiting = asyncio.create_task(
                MetricsService(database.new_metrics_uow).read(today, today + timedelta(days=1))
            )
            # Ensure the waiting transaction exists before a later source commit.
            await asyncio.sleep(0.15)
            async with database.new_metrics_uow() as source:
                await Users(source.session).insert("late@example.test", "synthetic")
                await source.commit()
            boundary = await blocking.session.scalar(text("SELECT clock_timestamp()"))
            await blocking.commit()
        row = (await waiting)[0]
        assert row["registered_profiles"] == 1
        assert row["calculated_at"] >= row["data_through"] >= boundary
        results = await asyncio.gather(
            *(
                MetricsService(database.new_metrics_uow).read(today, today + timedelta(days=1))
                for _ in range(3)
            )
        )
        assert all(result[0]["registered_profiles"] == 1 for result in results)
        await database.close()

    asyncio.run(exercise())


def test_pre0006_metrics_are_explicitly_unavailable(disposable_url):
    prepare(disposable_url, "0005_llm_workflow")

    async def exercise():
        database = Database(normalize_url(disposable_url))
        today = datetime.now(UTC).date()
        assert (
            await MetricsService(database.new_metrics_uow).read(today, today + timedelta(days=1))
            == []
        )
        await database.close()

    asyncio.run(exercise())


def test_late_provider_accounting_rewrites_physical_start_date_without_event(disposable_url):
    from scope_guard.database.repositories.llm import LlmSQLStore
    from scope_guard.domain.llm.runtime import ProviderResponse

    prepare(disposable_url)

    async def exercise():
        database = Database(normalize_url(disposable_url))
        day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=1
        )
        owner = await seed(database, day)
        excluded = await seed(database, day, excluded=True)
        call_ids = []
        for identity in (owner, excluded):
            async with database.new_uow() as work:
                op = await work.session.scalar(
                    text("""
                INSERT INTO llm_operations(owner_id,project_id,draft_id,source_revision,kind,
                 command_key,request_hash,frozen_input,input_hash,policy,status,created_at,
                 deadline_at,finished_at,reserved)
                VALUES(:owner,:project,:draft,1,'regenerate',:key,'fixture','{}','fixture',
                 jsonb_build_object('inputRate','0.001','outputRate','0.002'),
                 'failed',:stamp,:stamp+interval '1 minute',:stamp+interval '1 minute',4)
                RETURNING id
                """),
                    {**identity, "key": uuid4()},
                )
                for index, semantic, transport in ((1, 1, 1), (2, 1, 1), (3, 1, 2), (4, 2, 2)):
                    step = await work.session.scalar(
                        text("""
                    INSERT INTO llm_steps(operation_id,stage_key,input_hash,
                     prompt_version,schema_version)
                    VALUES(:op,:stage,'fixture','fixture','fixture') RETURNING id
                    """),
                        {"op": op, "stage": str(index)},
                    )
                    call = await work.session.scalar(
                        text("""
                    INSERT INTO provider_calls(operation_id,step_id,physical_index,semantic_attempt,
                     transport_attempt,epoch,requested_model,reasoning_effort,request_hash,
                     status,reserved_cost,started_at)
                    VALUES(:op,:step,:idx,:semantic,:transport,1,'controlled','low','fixture',
                     'unknown',1,:stamp) RETURNING id
                    """),
                        {
                            "op": op,
                            "step": step,
                            "idx": index,
                            "semantic": semantic,
                            "transport": transport,
                            "stamp": day,
                        },
                    )
                    if identity is owner:
                        call_ids.append(call)
                await work.commit()
        metrics = MetricsService(database.new_metrics_uow)
        row = (await metrics.read(day.date(), day.date() + timedelta(days=1)))[0]
        assert row["ai_calls"] == 4 and row["ai_retries"] == 2
        assert row["ai_cost_unknown_calls"] == row["ai_usage_unknown_calls"] == 4
        assert row["ai_estimated_cost_usd"] is None and row["input_tokens"] is None
        store = LlmSQLStore(database.new_uow)
        for call in call_ids:
            await store.complete(
                call, ProviderResponse("received late", input_tokens=10, output_tokens=20)
            )
        # Inspect persisted rows directly: complete() must trigger T2 without a business event/read.
        async with database.new_uow() as work:
            rows = (
                (
                    await work.session.execute(
                        text("SELECT * FROM marketing_metrics WHERE report_date=:day"),
                        {"day": day.date()},
                    )
                )
                .mappings()
                .one()
            )
            assert rows["ai_estimated_cost_usd"] == Decimal("0.2")
            assert rows["input_tokens"] == 40 and rows["output_tokens"] == 80
            assert rows["ai_cost_unknown_calls"] == rows["ai_usage_unknown_calls"] == 0
            assert rows["cached_tokens"] is None and rows["reasoning_tokens"] is None
            assert rows["dau"] == 0  # Failed regeneration and provider calls create no activity.
        await database.close()

    asyncio.run(exercise())


def test_concurrent_commits_distinct_profiles_and_same_run_archive(disposable_url):
    prepare(disposable_url)

    async def exercise():
        database = Database(normalize_url(disposable_url))
        day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=1
        )
        owners = [await seed(database, day) for _ in range(3)]
        runs = await asyncio.gather(*(saved_check(database, owner) for owner in owners))
        # A later durable regeneration references the synchronous baseline run;
        # it does not own that original check and must not suppress its count.
        async with database.new_uow() as work:
            await work.session.execute(
                text("""
            INSERT INTO llm_operations(owner_id,project_id,draft_id,source_revision,
             analysis_run_id,kind,command_key,request_hash,frozen_input,input_hash,policy,
             status,created_at,deadline_at,finished_at)
            VALUES(:owner,:project,:draft,1,:run,'regenerate',:key,'fixture','{}','fixture','{}',
             'failed',:stamp,:stamp+interval '1 minute',:stamp+interval '1 minute')
            """),
                {**owners[0], "run": runs[0][0], "key": uuid4()},
            )
            await work.commit()
        await asyncio.gather(*(saved_check(database, owners[0], run=runs[0][0]) for _ in range(3)))
        results = await asyncio.gather(
            *(
                MetricsService(database.new_metrics_uow).read(
                    day.date(), day.date() + timedelta(days=1)
                )
                for _ in range(3)
            )
        )
        for result in results:
            assert result[0]["dau"] == result[0]["mau"] == result[0]["check_succeeded"] == 3
            assert result[0]["regeneration_failed"] == 1
        await database.close()

    asyncio.run(exercise())


def test_partial_t2_write_rolls_back_atomically_and_next_read_repairs(disposable_url, monkeypatch):
    from scope_guard.database.repositories.marketing import MarketingRepository

    prepare(disposable_url)

    async def exercise():
        database = Database(normalize_url(disposable_url))
        today = datetime.now(UTC).date()
        metrics = MetricsService(database.new_metrics_uow)
        before = (await metrics.read(today, today + timedelta(days=1)))[0]
        async with database.new_metrics_uow() as source:
            await Users(source.session).insert("atomic@example.test", "synthetic")
            await source.commit()
        original = MarketingRepository.save

        async def interrupted(repository, rows):
            await original(repository, rows[:1])
            raise RuntimeError("interrupted T2 write")

        with monkeypatch.context() as patch:
            patch.setattr(MarketingRepository, "save", interrupted)
            with pytest.raises(RuntimeError, match="interrupted T2"):
                await metrics.read(today, today + timedelta(days=1))
        async with database.new_uow() as work:
            persisted = (
                (await work.session.execute(text("SELECT * FROM marketing_metrics")))
                .mappings()
                .one()
            )
            assert dict(persisted) == before
            assert await work.session.scalar(text("SELECT count(*) FROM profiles")) == 1
        assert (await metrics.read(today, today + timedelta(days=1)))[0]["registered_profiles"] == 1
        await database.close()

    asyncio.run(exercise())
