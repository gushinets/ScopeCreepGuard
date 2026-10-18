"""Short independent transactions for execution, fencing, and attempt accounting."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from scope_guard.database.repositories.activity import llm_event, profiles_supported
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.llm.runtime import PROMPT_VERSION, GatewayFailure, digest, encode


async def one(work, sql, parameters=None):
    row = (await work.session.execute(text(sql), parameters or {})).mappings().first()
    return dict(row) if row else None


class LlmSQLStore:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def is_transient(error):
        return isinstance(error, DBAPIError)

    async def abandon(self, identifier, epoch):
        async with self.factory() as work:
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET lease_expires_at=now(), "
                    "worker_id=NULL WHERE id=:id AND epoch=:epoch AND status='running'"
                ),
                {"id": identifier, "epoch": epoch},
            )
            await work.commit()

    async def prior(self, owner, project, command, request_hash):
        async with self.factory() as work:
            row = await one(
                work,
                "SELECT * FROM llm_operations WHERE owner_id=:owner AND "
                "project_id=:project AND command_key=:key",
                {"owner": owner, "project": project, "key": command},
            )
        if row and row["request_hash"] != request_hash:
            raise WorkflowError("operationMismatch", 409)
        return row

    async def get(self, owner, identifier):
        async with self.factory() as work:
            row = await one(
                work,
                "SELECT * FROM llm_operations WHERE id=:id AND owner_id=:owner",
                {"id": identifier, "owner": owner},
            )
        if not row:
            raise WorkflowError("analysisNotFound", 404)
        return row

    async def steps(self, identifier):
        async with self.factory() as work:
            return [
                dict(r)
                for r in (
                    await work.session.execute(
                        text("SELECT * FROM llm_steps WHERE operation_id=:id ORDER BY stage_key"),
                        {"id": identifier},
                    )
                )
                .mappings()
                .all()
            ]

    async def claim(self, worker, *, lane="user"):
        if lane not in ("user", "diagnostic"):
            raise ValueError("invalid_llm_lane")
        kind_filter = (
            "kind='diagnostic'"
            if lane == "diagnostic"
            else "kind IN ('check','regenerate','translate','estimate','agreement')"
        )
        async with self.factory() as work:
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET status='failed', "
                    "error=CAST(:error AS jsonb), "
                    "finished_at=now(),lease_expires_at=NULL WHERE status IN ('queued','running') "
                    "AND deadline_at<=now()"
                ),
                {"error": encode({"code": "errors.operationDeadlineExceeded", "status": 502})},
            )
            await self.fail_runs(work)
            await work.session.execute(
                text(
                    "UPDATE provider_calls SET status='unknown', "
                    "finished_at=now(),error=CAST(:error AS jsonb) WHERE status='in_flight' AND "
                    "operation_id IN (SELECT id FROM llm_operations WHERE status='failed')"
                ),
                {"error": encode({"code": "providerOutcomeUnknown"})},
            )
            row = await one(
                work,
                f"SELECT * FROM llm_operations WHERE {kind_filter} AND (status='queued' OR "
                "(status='running' AND lease_expires_at<=now())) ORDER BY created_at,id "
                "LIMIT 1 FOR UPDATE SKIP LOCKED",
            )
            if row:
                await work.session.execute(
                    text(
                        "UPDATE provider_calls SET status='unknown', "
                        "finished_at=now(),error=CAST(:error AS jsonb) "
                        "WHERE operation_id=:id AND status='in_flight'"
                    ),
                    {"id": row["id"], "error": encode({"code": "providerOutcomeUnknown"})},
                )
                row = await one(
                    work,
                    "UPDATE llm_operations SET status='running',epoch=epoch+1, "
                    "worker_id=:worker,lease_expires_at=LEAST(deadline_at,now()+interval "
                    "'90 seconds') "
                    "WHERE id=:id RETURNING *",
                    {"worker": worker, "id": row["id"]},
                )
            await work.commit()
        return row

    async def renew(self, identifier, epoch):
        async with self.factory() as work:
            row = await one(
                work,
                "UPDATE llm_operations SET lease_expires_at="
                "LEAST(deadline_at,now()+interval '90 seconds') WHERE id=:id AND epoch=:epoch "
                "AND status='running' AND lease_expires_at>now() AND deadline_at>now() "
                "RETURNING id",
                {"id": identifier, "epoch": epoch},
            )
            await work.commit()
        return row is not None

    async def owned(self, work, binding):
        row = await one(
            work,
            "SELECT * FROM llm_operations WHERE id=:id AND epoch=:epoch AND "
            "status='running' AND lease_expires_at>now() AND deadline_at>now() FOR UPDATE",
            {"id": binding.operation_id, "epoch": binding.epoch},
        )
        if not row:
            raise GatewayFailure("operationLeaseLost")
        return row

    async def freeze_stage(self, binding, input_hash):
        async with self.factory() as work:
            await self.owned(work, binding)
            step = await one(
                work, "SELECT * FROM llm_steps WHERE id=:id FOR UPDATE", {"id": binding.step_id}
            )
            if step["status"] != "pending" and step["input_hash"] != input_hash:
                raise GatewayFailure("workflowVersionUnavailable")
            await work.session.execute(
                text("UPDATE llm_steps SET input_hash=:hash WHERE id=:id"),
                {"hash": input_hash, "id": binding.step_id},
            )
            await work.commit()

    async def reserve(self, request, transport_attempt):
        async with self.factory() as work:
            operation = await self.owned(work, request.binding)
            step = await one(
                work,
                "SELECT * FROM llm_steps WHERE id=:step AND operation_id=:op FOR UPDATE",
                {"step": request.binding.step_id, "op": operation["id"]},
            )
            if not step or step["status"] == "accepted" or request.semantic_attempt > 3:
                raise GatewayFailure("semanticAttemptsExhausted")
            if (request.semantic_attempt, transport_attempt) not in (
                (step["semantic_attempt"] + 1, 1),
                (step["semantic_attempt"], step["transport_attempt"] + 1),
            ):
                raise GatewayFailure("attemptSequenceInvalid")
            policy = operation["policy"]
            if request.binding.model != policy["model"]:
                raise GatewayFailure("providerModelMismatch")
            # Each UTF-8 byte is a conservative OpenAI text-token upper bound; include schema
            # and a framing allowance. Refuse oversized input rather than guess token usage.
            upper_input = (
                len(
                    json.dumps(
                        {"messages": request.messages, "schema": request.schema}, ensure_ascii=False
                    ).encode("utf-8")
                )
                + 256
            )
            if upper_input > 32768:
                raise GatewayFailure("analysisInputTooLarge")
            if not 0 < request.max_output_tokens <= 4096:
                raise GatewayFailure("operationBudgetExceeded")
            rate_in, rate_out = Decimal(policy["inputRate"]), Decimal(policy["outputRate"])
            reserved = upper_input * rate_in + request.max_output_tokens * rate_out
            if operation["physical_calls"] >= policy["maxCalls"] or (
                operation["spent"] + operation["reserved"] + reserved > Decimal(policy["maxCost"])
            ):
                raise GatewayFailure("operationBudgetExceeded")
            index = operation["physical_calls"] + 1
            row = await one(
                work,
                "INSERT INTO provider_calls(operation_id,step_id,physical_index, "
                "semantic_attempt,transport_attempt,epoch,requested_model,reasoning_effort, "
                "request_hash,status, "
                "reserved_cost) "
                "VALUES(:op,:step,:physical,:semantic,:transport,:epoch,:model,:effort, "
                ":request_hash,'in_flight',:cost) RETURNING id",
                {
                    "op": operation["id"],
                    "step": step["id"],
                    "physical": index,
                    "semantic": request.semantic_attempt,
                    "transport": transport_attempt,
                    "epoch": request.binding.epoch,
                    "model": request.binding.model,
                    "effort": request.binding.effort,
                    "request_hash": digest(
                        {"messages": request.messages, "schema": request.schema}
                    ),
                    "cost": reserved,
                },
            )
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET physical_calls=:calls, "
                    "reserved=reserved+:cost WHERE id=:id"
                ),
                {"calls": index, "cost": reserved, "id": operation["id"]},
            )
            await work.session.execute(
                text(
                    "UPDATE llm_steps SET status='running', "
                    "semantic_attempt=:semantic,transport_attempt=:transport,candidate=NULL, "
                    "prepared_request=CAST(:request AS jsonb) "
                    "WHERE id=:id"
                ),
                {
                    "id": step["id"],
                    "semantic": request.semantic_attempt,
                    "transport": transport_attempt,
                    "request": encode(
                        {
                            "messages": request.messages,
                            "schema": request.schema,
                            "schemaName": request.schema_name,
                        }
                    ),
                },
            )
            work.session.info["marketing_metrics_dirty"] = True
            await work.commit()
        return row["id"]

    async def call(self, identifier):
        async with self.factory() as work:
            return await one(work, "SELECT * FROM provider_calls WHERE id=:id", {"id": identifier})

    async def complete(self, identifier, response=None, error=None):
        async with self.factory() as work:
            call = await one(work, "SELECT * FROM provider_calls WHERE id=:id", {"id": identifier})
            if not call:
                return
            operation = await one(
                work,
                "SELECT * FROM llm_operations WHERE id=:id FOR UPDATE",
                {"id": call["operation_id"]},
            )
            call = await one(
                work, "SELECT * FROM provider_calls WHERE id=:id FOR UPDATE", {"id": identifier}
            )
            if call["status"] in ("completed", "failed"):
                return
            policy = operation["policy"]
            estimate = None
            if (
                response
                and response.input_tokens is not None
                and response.output_tokens is not None
            ):
                estimate = response.input_tokens * Decimal(policy["inputRate"]) + (
                    response.output_tokens * Decimal(policy["outputRate"])
                )
            reported = response.reported_cost if response else None
            assessed = max([v for v in (estimate, reported) if v is not None], default=None)
            status = (
                "completed"
                if response
                else "unknown"
                if (error or {}).get("uncertain")
                else "failed"
            )
            await work.session.execute(
                text(
                    "UPDATE provider_calls SET status=:status, "
                    "actual_model=:model,actual_provider=:provider,response_id=:response, "
                    "provider_request_id=:request,input_tokens=:input,output_tokens=:output, "
                    "output_status=:output_status, "
                    "cached_tokens=:cached,reasoning_tokens=:reasoning,reported_cost=:reported, "
                    "estimated_cost=:estimate,cost_status=:cost_status,usage_status=:usage_status, "
                    "error=CAST(:error AS jsonb),finished_at=now(), "
                    "latency_ms=greatest(0,extract(epoch from (now()-started_at))*1000)::integer "
                    "WHERE id=:id"
                ),
                {
                    "id": identifier,
                    "status": status,
                    "model": response.model if response else None,
                    "provider": response.provider if response else None,
                    "response": response.response_id if response else None,
                    "request": response.request_id if response else None,
                    "output_status": response.status if response else None,
                    "input": response.input_tokens if response else None,
                    "output": response.output_tokens if response else None,
                    "cached": response.cached_tokens if response else None,
                    "reasoning": response.reasoning_tokens if response else None,
                    "reported": reported,
                    "estimate": estimate,
                    "cost_status": "reported"
                    if reported is not None
                    else "estimated"
                    if estimate is not None
                    else "unknown",
                    "usage_status": "reported" if estimate is not None else "unknown",
                    "error": encode(error) if error else None,
                },
            )
            if assessed is not None:
                await work.session.execute(
                    text(
                        "UPDATE llm_operations SET spent=spent+:cost, "
                        "reserved=reserved-:reservation WHERE id=:id"
                    ),
                    {"id": operation["id"], "cost": assessed, "reservation": call["reserved_cost"]},
                )
                if assessed > call["reserved_cost"]:
                    discrepancy = {
                        "code": "providerCostBoundExceeded",
                        "reserved": str(call["reserved_cost"]),
                        "assessed": str(assessed),
                    }
                    await work.session.execute(
                        text("UPDATE provider_calls SET error=CAST(:error AS jsonb) WHERE id=:id"),
                        {"id": identifier, "error": encode(discrepancy)},
                    )
                    await work.session.execute(
                        text(
                            "UPDATE llm_operations SET status='failed', "
                            "error=CAST(:error AS jsonb),finished_at=now(),lease_expires_at=NULL "
                            "WHERE id=:id AND status IN ('queued','running')"
                        ),
                        {
                            "id": operation["id"],
                            "error": encode(
                                {
                                    "code": "errors.operationBudgetExceeded",
                                    "status": 502,
                                    "rule": "provider_cost_bound",
                                    "callId": str(identifier),
                                }
                            ),
                        },
                    )
                    await self.fail_runs(work)
            # Candidate and received accounting commit together. Old executors may account
            # their own calls, but can never write a candidate or accept/publish a stage.
            if response and response.status == "completed" and response.text.strip():
                await work.session.execute(
                    text(
                        "UPDATE llm_steps SET candidate=:candidate WHERE "
                        "id=:step AND status<>'accepted' AND EXISTS(SELECT 1 FROM "
                        "llm_operations WHERE "
                        "id=:op AND epoch=:epoch AND status='running' AND lease_expires_at>now() "
                        "AND deadline_at>now())"
                    ),
                    {
                        "candidate": response.text,
                        "step": call["step_id"],
                        "op": operation["id"],
                        "epoch": call["epoch"],
                    },
                )
            work.session.info["marketing_metrics_dirty"] = True
            await work.commit()

    async def checkpoint(self, request, response):
        # complete() already commits the candidate atomically with call accounting.
        return None

    async def accept(self, binding, value):
        async with self.factory() as work:
            operation = await self.owned(work, binding)
            if operation["spent"] + operation["reserved"] > Decimal(operation["policy"]["maxCost"]):
                raise GatewayFailure("operationBudgetExceeded")
            await work.session.execute(
                text(
                    "UPDATE llm_steps SET status='accepted', "
                    "accepted_result=CAST(:result AS jsonb),candidate=NULL,feedback=NULL "
                    "WHERE id=:id "
                    "AND operation_id=:op AND status<>'accepted'"
                ),
                {"id": binding.step_id, "op": binding.operation_id, "result": encode(value)},
            )
            await work.session.execute(
                text(
                    "UPDATE provider_calls SET validation_status='accepted' "
                    "WHERE id=(SELECT id FROM provider_calls WHERE step_id=:step "
                    "AND status='completed' "
                    "ORDER BY physical_index DESC LIMIT 1)"
                ),
                {"step": binding.step_id},
            )
            work.session.info["marketing_metrics_dirty"] = True
            await work.commit()

    async def feedback(self, binding, error):
        async with self.factory() as work:
            await self.owned(work, binding)
            await work.session.execute(
                text(
                    "UPDATE llm_steps SET feedback=CAST(:error AS jsonb) "
                    "WHERE id=:id AND status<>'accepted'"
                ),
                {"id": binding.step_id, "error": encode(error)},
            )
            await work.session.execute(
                text(
                    "UPDATE provider_calls SET validation_status='rejected', "
                    "error=CAST(:error AS jsonb) WHERE id=(SELECT id FROM provider_calls WHERE "
                    "step_id=:step AND status='completed' ORDER BY physical_index DESC LIMIT 1)"
                ),
                {"step": binding.step_id, "error": encode({"code": "validationRejected", **error})},
            )
            work.session.info["marketing_metrics_dirty"] = True
            await work.commit()

    async def finish_diagnostics(self, operation):
        async with self.factory() as work:
            await self.owned(
                work,
                SimpleNamespace(operation_id=operation["id"], epoch=operation["epoch"]),
            )
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET status='succeeded',result='{}'::jsonb,"
                    "finished_at=now(),lease_expires_at=NULL WHERE id=:id AND epoch=:epoch"
                ),
                {"id": operation["id"], "epoch": operation["epoch"]},
            )
            await work.commit()

    async def fail(self, identifier, epoch, code, status=502):
        async with self.factory() as work:
            rule = await one(
                work,
                "SELECT stage_key,feedback FROM llm_steps WHERE operation_id=:id "
                "AND status<>'accepted' AND feedback IS NOT NULL "
                "ORDER BY semantic_attempt DESC LIMIT 1",
                {"id": identifier},
            )
            await work.session.execute(
                text(
                    "UPDATE llm_operations SET status='failed', "
                    "error=CAST(:error AS jsonb),finished_at=now(),lease_expires_at=NULL "
                    "WHERE id=:id AND epoch=:epoch AND status='running' AND lease_expires_at>now()"
                ),
                {
                    "id": identifier,
                    "epoch": epoch,
                    "error": encode(
                        {
                            "code": "errors." + code,
                            "status": status,
                            **(
                                {"stage": rule["stage_key"], "rule": rule["feedback"]["rule"]}
                                if rule
                                else {}
                            ),
                        }
                    ),
                },
            )
            await self.fail_runs(work)
            await work.commit()

    async def fail_runs(self, work):
        await work.session.execute(
            text(
                "UPDATE llm_steps SET status='failed' WHERE status<>'accepted' "
                "AND operation_id IN (SELECT id FROM llm_operations WHERE status='failed')"
            )
        )
        # ANY-549 requires pending -> running -> failed. Reconcile terminal check operations.
        for current, target in (("pending", "running"), ("running", "failed")):
            await work.session.execute(
                text(
                    "UPDATE analysis_runs SET status=:target, "
                    "started_at=coalesce(started_at,now()),finished_at=CASE WHEN :target='failed' "
                    "THEN now() ELSE NULL END,error_code=CASE WHEN :target='failed' THEN "
                    "'llm_operation_failed' ELSE NULL END WHERE status=:current AND id IN "
                    "(SELECT analysis_run_id FROM llm_operations WHERE "
                    "kind IN ('check','estimate') AND "
                    "status='failed')"
                ),
                {"target": target, "current": current},
            )
        if await profiles_supported(work.session):
            rows = (
                (
                    await work.session.execute(
                        text(
                            "SELECT o.* FROM llm_operations o WHERE o.status='failed' AND "
                            "o.kind<>'diagnostic' "
                            "AND NOT EXISTS "
                            "(SELECT 1 FROM activity_events e WHERE e.project_id=o.project_id "
                            "AND e.operation_id=o.command_key AND e.event_type IN "
                            "('check.failed','estimate.failed',"
                            "'translation.failed','reply.failed')) "
                            "ORDER BY o.id FOR UPDATE OF o"
                        )
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                await llm_event(work.session, dict(row), "failed")


class LlmTransactionRepository:
    """Admission writes participate in the existing workflow UoW."""

    def __init__(self, session):
        self.session = session

    async def fence(self, operation):
        row = await one(
            self,
            "SELECT * FROM llm_operations WHERE id=:id AND epoch=:epoch "
            "AND status='running' AND lease_expires_at>now() AND deadline_at>now() FOR UPDATE",
            {"id": operation["id"], "epoch": operation["epoch"]},
        )
        if not row:
            raise GatewayFailure("operationLeaseLost")
        if row["spent"] + row["reserved"] > Decimal(row["policy"]["maxCost"]):
            raise GatewayFailure("operationBudgetExceeded")
        if await profiles_supported(self.session):
            self.session.info["activity_executor"] = "system"
            self.session.info["activity_origin_session"] = await self.session.scalar(
                text(
                    "SELECT product_session_id FROM activity_events WHERE project_id=:project "
                    "AND operation_id=:key AND event_type LIKE '%.requested' "
                    "ORDER BY created_at LIMIT 1"
                ),
                {"project": row["project_id"], "key": row["command_key"]},
            )
        return row

    async def publish(self, operation, envelope):
        await self.fence(operation)
        await self.session.execute(
            text(
                "UPDATE llm_operations SET status='succeeded', "
                "result=CAST(:result AS jsonb),finished_at=now(),lease_expires_at=NULL "
                "WHERE id=:id "
                "AND epoch=:epoch"
            ),
            {"id": operation["id"], "epoch": operation["epoch"], "result": encode(envelope)},
        )
        await llm_event(self.session, operation, "completed", envelope)
        if operation["kind"] != "diagnostic":
            await self.enqueue_diagnostics(operation)

    async def active_agreement(self, owner, draft):
        return await one(
            self,
            "SELECT * FROM llm_operations WHERE owner_id=:owner AND draft_id=:draft "
            "AND kind='agreement' AND status IN ('queued','running') ORDER BY created_at LIMIT 1",
            {"owner": owner, "draft": draft},
        )

    async def restore_existing(self, operation, envelope):
        await self.session.execute(
            text(
                "UPDATE llm_operations SET status='succeeded',result=CAST(:result AS "
                "jsonb),error=NULL WHERE id=:id"
            ),
            {"id": operation["id"], "result": encode(envelope)},
        )

    async def enqueue_diagnostics(self, operation):
        # Same commit as user publication; replay cannot create another review job.
        parent = await one(
            self, "SELECT * FROM llm_operations WHERE id=:id", {"id": operation["id"]}
        )
        stages = (
            (
                await self.session.execute(
                    text(
                        "SELECT stage_key FROM llm_steps WHERE operation_id=:id AND "
                        "status='accepted' "
                        "ORDER BY stage_key"
                    ),
                    {"id": operation["id"]},
                )
            )
            .scalars()
            .all()
        )
        timestamp = datetime.now(UTC)
        policy = dict(parent["policy"])
        policy["maxCost"] = str(
            max(Decimal(0), Decimal(policy["maxCost"]) - parent["spent"] - parent["reserved"])
        )
        review_calls = 2 * sum(stage != "analysis" for stage in stages)
        policy["maxCalls"] = min(
            review_calls, max(0, policy["maxCalls"] - parent["physical_calls"])
        )
        frozen = {"parentId": str(parent["id"]), "contract": "diagnostics-v1"}
        command = uuid5(
            UUID("66366366-3663-4663-8663-663663663663"), str(parent["id"]) + ":diagnostics"
        )
        values = {
            "owner": parent["owner_id"],
            "project": parent["project_id"],
            "draft": parent["draft_id"],
            "revision": parent["source_revision"],
            "run": parent["analysis_run_id"],
            "kind": "diagnostic",
            "key": command,
            "hash": digest(frozen),
            "input": encode(frozen),
            "input_hash": digest(frozen),
            "policy": encode(policy),
            "status": "queued",
            "error": None,
            "deadline": timestamp + timedelta(seconds=180),
            "finished": None,
        }
        if not await self.prior(parent["owner_id"], parent["project_id"], command):
            await self.insert(
                values,
                tuple(
                    key for stage in stages for key in (stage + "_diagnostic", stage + "_review_1")
                ),
            )

    async def prior(self, owner, project, command):
        return await one(
            self,
            "SELECT * FROM llm_operations WHERE owner_id=:owner AND "
            "project_id=:project AND command_key=:key",
            {"owner": owner, "project": project, "key": command},
        )

    async def insert(self, values, stages):
        row = await one(
            self,
            "INSERT INTO llm_operations(owner_id,project_id,draft_id, "
            "source_revision,analysis_run_id,kind,command_key,request_hash,frozen_input,i"
            "nput_hash, "
            "policy,status,error,deadline_at,finished_at) VALUES(:owner,:project,:draft,:revision, "
            ":run,:kind,:key,:hash,CAST(:input AS jsonb),:input_hash,CAST(:policy AS "
            "jsonb),:status, "
            "CAST(:error AS jsonb),:deadline,:finished) RETURNING *",
            values,
        )
        for stage in stages:
            await self.session.execute(
                text(
                    "INSERT INTO llm_steps(operation_id,stage_key, "
                    "input_hash,prompt_version,schema_version) "
                    "VALUES(:op,:stage,:hash,:prompt, "
                    "'stage-v1')"
                ),
                {
                    "op": row["id"],
                    "stage": stage,
                    "hash": values["input_hash"],
                    "prompt": PROMPT_VERSION,
                },
            )
        if row["kind"] not in ("check", "estimate"):
            await llm_event(self.session, row, "requested")
        if row["status"] == "failed":
            await llm_event(self.session, row, "failed")
        return row
