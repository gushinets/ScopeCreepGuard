"""Restart-safe fixed-stage execution; HTTP requests never own these tasks."""

import asyncio
import logging
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from scope_guard.domain.analysis.normalization import parse_snapshot
from scope_guard.domain.analysis.serialization import analysis_to_wire
from scope_guard.domain.change_orders.estimation import commercial_signature
from scope_guard.domain.change_orders.merge import merge_estimate
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.llm.runtime import PROMPT_VERSION, Binding, GatewayFailure, digest
from scope_guard.services.drafts.workflow import context, formed_document, generation_context

NAMESPACE = UUID("66366366-3663-4663-8663-663663663663")


class LlmWorker:
    def __init__(self, factory, store, runner, *, worker_id=None):
        self.factory, self.store, self.runner = factory, store, runner
        self.worker_id = worker_id or str(uuid4())
        self.stopping = asyncio.Event()

    async def process_one(self):
        operation = await self.store.claim(self.worker_id)
        if operation is None:
            return False
        task = asyncio.create_task(self.execute(operation))
        lease_lost = False

        async def heartbeat():
            nonlocal lease_lost
            while not task.done():
                await asyncio.sleep(15)
                try:
                    valid = await self.store.renew(operation["id"], operation["epoch"])
                except Exception:
                    valid = False
                if not valid:
                    lease_lost = True
                    task.cancel()
                    return

        renewal = asyncio.create_task(heartbeat())
        try:
            remaining = (operation["deadline_at"] - datetime.now(UTC)).total_seconds()
            async with asyncio.timeout(max(0, remaining)):
                await task
        except asyncio.CancelledError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if not lease_lost:
                await asyncio.shield(self.store.abandon(operation["id"], operation["epoch"]))
                raise
        except Exception as error:
            if self.store.is_transient(error):
                await self.store.abandon(operation["id"], operation["epoch"])
                logging.getLogger("scope_guard").error("llm_publication_deferred")
                return False
            code = (
                error.code
                if isinstance(error, GatewayFailure)
                else (
                    error.code.removeprefix("errors.")
                    if isinstance(error, WorkflowError)
                    else "operationDeadlineExceeded"
                    if isinstance(error, TimeoutError)
                    else "analysisInvalid"
                )
            )
            await self.store.fail(
                operation["id"],
                operation["epoch"],
                code,
                error.status if isinstance(error, WorkflowError) else 502,
            )
        finally:
            renewal.cancel()
            await asyncio.gather(renewal, return_exceptions=True)
        return True

    async def stage(self, operation, stage, facts):
        if operation["policy"].get("version") != "workflow-policy-v1":
            raise GatewayFailure("workflowVersionUnavailable")
        record = next(s for s in await self.store.steps(operation["id"]) if s["stage_key"] == stage)
        if record["prompt_version"] != PROMPT_VERSION or record["schema_version"] != "stage-v1":
            raise GatewayFailure("workflowVersionUnavailable")
        start, transport = record["semantic_attempt"], 0
        if record["status"] != "accepted" and start and not record["candidate"]:
            if record["transport_attempt"] >= 2:
                raise GatewayFailure("transportAttemptsExhausted")
            start, transport = start - 1, record["transport_attempt"]
        binding = Binding(
            operation["id"],
            record["id"],
            operation["epoch"],
            operation["policy"]["model"],
            "high" if stage == "reply" else "medium",
            start,
            operation["deadline_at"],
            transport,
        )
        await self.store.freeze_stage(binding, digest(facts))
        if record["status"] == "accepted":
            return record["accepted_result"]
        value = await self.runner.run(binding, stage, facts, record)
        await self.store.accept(binding, value)
        return value

    async def execute(self, operation):
        if digest(operation["frozen_input"]) != operation["input_hash"]:
            raise GatewayFailure("workflowVersionUnavailable")
        if operation["kind"] == "diagnostic":
            await self.runner.diagnose(operation)
            return
        facts = deepcopy(operation["frozen_input"])
        kind = operation["kind"]
        if kind in ("check", "estimate"):
            async with self.factory() as work:
                await work.llm.fence(operation)
                run = await work.workflow.run(operation["owner_id"], operation["analysis_run_id"])
                if run["status"] == "pending":
                    await work.workflow.finish_run(
                        operation["owner_id"], operation["analysis_run_id"], "running", None
                    )
                await work.commit()
        if kind == "check":
            analysis = await self.stage(operation, "analysis", facts)
            facts["analysis"] = analysis
            replies = await self.stage(operation, "replies", facts)
            result = {
                k: v
                for k, v in analysis.items()
                if k not in ("estimatedHours", "additionalCost", "currency")
            }
            result.update(
                replies={k: replies[k] for k in ("warm", "neutral", "firm")},
                clientLanguage=facts["selection"]["selectedLanguage"],
                changeOrder=None,
                estimate={k: analysis[k] for k in ("estimatedHours", "additionalCost", "currency")},
            )
            project = facts["project"]
            result["commercialSignature"] = commercial_signature(
                generation_context(str(operation["project_id"]), project), project.get("endDate")
            )
            result["draftCreatedAt"] = facts["createdAt"]
            result["requestLanguage"] = (
                facts["selection"]["language"] or facts["selection"]["selectedLanguage"]
            )
            result["estimateValid"] = bool(project.get("pricingModel") and project.get("currency"))
            result = analysis_to_wire(parse_snapshot(result, facts["locale"]))
            document = formed_document(
                result, project, result["clientLanguage"], facts["createdAt"]
            )
            document["languageSelection"] = facts["selection"]
            await self.publish_check(operation, result, document)
        else:
            document = facts["document"]
            if kind == "regenerate":
                variant = await self.stage(operation, "reply", facts)
                reply = document["reply"]
                reply["text"] = variant["text"]
                reply["generated"][reply["tone"]] = variant["text"]
            elif kind == "agreement":
                if document.get("changeOrder") is None:
                    if facts.get("prepareEstimate"):
                        estimate = await self.stage(operation, "estimate", facts)
                        facts["analysis"].update(
                            {
                                k: estimate[k]
                                for k in ("estimatedHours", "additionalCost", "currency")
                            }
                        )
                    order = await self.stage(operation, "change_order", facts)
                    source = {
                        **facts["analysis"],
                        "replies": document["reply"]["generated"],
                        "changeOrderLabels": order["labels"],
                        "changeOrder": {
                            **{
                                k: order[k]
                                for k in ("description", "timelineImpact", "rationale", "note")
                            },
                            **{
                                k: facts["analysis"].get(k, "")
                                for k in ("estimatedHours", "additionalCost", "currency")
                            },
                        },
                    }
                    # Explicit preparation is allowed for every verdict.
                    document["changeOrder"] = formed_document(
                        source,
                        facts["project"],
                        document["reply"]["language"],
                        facts["createdAt"],
                        explicit=True,
                    )["changeOrder"]
                    document["changeOrder"]["additionalTerms"] = order["additionalTerms"]
                    document["estimate"] = {
                        "analysisRunId": str(operation["analysis_run_id"]),
                        "sourceDraftRevision": str(operation["source_revision"]),
                        "effectiveEndDate": document["changeOrder"].get("endDate") or None,
                        "commercialSignature": commercial_signature(
                            generation_context(str(operation["project_id"]), facts["project"]),
                            document["changeOrder"].get("endDate") or None,
                        ),
                        "estimateValid": bool(
                            facts.get("prepareEstimate") or facts["analysis"].get("estimateValid")
                        ),
                    }
            elif kind == "translate":
                replies, order = await self.material_stages(operation, facts)
                reply = document["reply"]
                reply["generated"] = {k: replies[k] for k in ("warm", "neutral", "firm")}
                reply["text"] = reply["generated"][reply["tone"]]
                reply["language"] = facts["selection"]["selectedLanguage"]
                if document["changeOrder"]:
                    old = deepcopy(document["changeOrder"])
                    document["changeOrder"].update(
                        {
                            k: order[k]
                            for k in (
                                "description",
                                "timelineImpact",
                                "rationale",
                                "note",
                                "additionalTerms",
                            )
                        }
                    )
                    document["changeOrder"].update(
                        language=reply["language"], changeOrderLabels=order["labels"]
                    )
                    for field in ("description", "timelineImpact", "rationale", "note"):
                        if old.get(field) == old.get("aiValues", {}).get(field):
                            document["changeOrder"]["aiValues"][field] = order[field]
            elif kind == "estimate":
                estimate = await self.stage(operation, "estimate", facts)
                order = document["changeOrder"]
                if order is None:
                    raise WorkflowError("analysisStale", 409)
                order = merge_estimate(
                    order,
                    {
                        field: str(estimate[field])
                        for field in ("estimatedHours", "additionalCost", "currency", "rationale")
                    },
                )
                document["changeOrder"] = order
                document["estimate"] = {
                    "analysisRunId": str(operation["analysis_run_id"]),
                    "sourceDraftRevision": str(operation["source_revision"]),
                    "effectiveEndDate": order.get("endDate") or facts["project"].get("endDate"),
                    "commercialSignature": commercial_signature(
                        generation_context(str(operation["project_id"]), facts["project"]),
                        order.get("endDate") or None,
                    ),
                    "estimateValid": True,
                }
            document["languageSelection"] = facts["selection"]
            await self.publish_document(operation, document)

    async def material_stages(self, operation, facts):
        # Await cancellation/accounting of both children before releasing ownership.
        tasks = [
            asyncio.create_task(self.stage(operation, stage, facts))
            for stage in (
                ("replies", "change_order")
                if facts["document"].get("changeOrder")
                else ("replies",)
            )
        ]
        try:
            values = await asyncio.gather(*tasks)
            return (values[0], values[1] if len(values) > 1 else None)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def publish_check(self, operation, result, document):
        owner, draft_id = operation["owner_id"], operation["draft_id"]
        facts = operation["frozen_input"]
        async with self.factory() as work:
            await work.llm.fence(operation)
            project = await work.workflow.project(owner, operation["project_id"], lock=True)
            run = await work.workflow.run(owner, operation["analysis_run_id"])
            if run["status"] != "succeeded":
                run = await work.workflow.finish_run(
                    owner, operation["analysis_run_id"], "succeeded", result
                )
            run = await work.workflow.run(owner, operation["analysis_run_id"])
            draft = await work.workflow.draft(owner, draft_id, lock=True)
            history_key = uuid5(NAMESPACE, str(operation["id"]) + ":history")
            history_hash = digest({"operation": str(operation["id"]), "publication": "history"})
            history = await work.workflow.history_operation(
                owner, operation["project_id"], history_key, history_hash
            )
            if not history:
                frozen_draft = {
                    **draft,
                    "revision": str(operation["source_revision"]),
                    "requestText": facts["request"],
                    "draftDocument": document,
                }
                history = await work.workflow.complete(
                    owner, frozen_draft, facts["project"], run, history_key, history_hash
                )
            applied = (
                int(draft["revision"]) == operation["source_revision"]
                and draft["requestText"] == facts["request"]
                and not project.get("archivedAt")
            )
            if applied:
                save_key = uuid5(NAMESPACE, str(operation["id"]) + ":apply")
                draft = await work.workflow.save(
                    owner,
                    draft_id,
                    operation["source_revision"],
                    save_key,
                    digest({"operation": str(operation["id"]), "publication": "apply"}),
                    {
                        "lastAnalysisRunId": run["id"],
                        "analysisIsStale": False,
                        "draftDocument": document,
                    },
                    "analysis_apply",
                    context(project),
                )
                draft["analysisRun"] = run
            envelope = {
                "analysisRun": run,
                "draft": draft if applied else None,
                "applied": applied,
                "historyEntryId": history["id"],
            }
            await work.llm.publish(operation, envelope)
            await work.commit()

    async def publish_document(self, operation, document):
        facts, owner = operation["frozen_input"], operation["owner_id"]
        async with self.factory() as work:
            await work.llm.fence(operation)
            project = await work.workflow.project(owner, operation["project_id"], lock=True)
            if project.get("archivedAt"):
                raise WorkflowError("projectArchived", 409)
            draft = await work.workflow.draft(owner, operation["draft_id"], lock=True)
            if int(draft["revision"]) != operation["source_revision"] or (
                draft["requestText"] != facts["request"]
            ):
                raise WorkflowError("draftConflict", 409)
            saved = await work.workflow.save(
                owner,
                operation["draft_id"],
                operation["source_revision"],
                uuid5(NAMESPACE, str(operation["id"]) + ":edit"),
                operation["request_hash"],
                {"draftDocument": document},
                "language_change"
                if operation["kind"] == "translate"
                else "change_order_edit"
                if operation["kind"] == "agreement"
                else "regenerate",
                context(project),
            )
            saved["analysisRun"] = await work.workflow.run(
                owner, UUID(facts["sourceAnalysisRunId"])
            )
            envelope = {"draft": saved}
            if operation["kind"] == "estimate":
                estimate = (await self.store.steps(operation["id"]))[0]["accepted_result"]
                source = deepcopy(facts["analysis"])
                source.update(
                    clientLanguage=document["reply"]["language"],
                    replies=document["reply"]["generated"],
                    estimateValid=True,
                    commercialSignature=document["estimate"]["commercialSignature"],
                )
                source["changeOrder"] = {
                    **(source.get("changeOrder") or {}),
                    **{
                        k: estimate[k]
                        for k in ("estimatedHours", "additionalCost", "currency", "rationale")
                    },
                }
                if document["changeOrder"].get("changeOrderLabels"):
                    source["changeOrderLabels"] = document["changeOrder"]["changeOrderLabels"]
                for field in ("description", "timelineImpact", "note"):
                    source["changeOrder"][field] = document["changeOrder"][field]
                run = await work.workflow.finish_run(
                    owner, operation["analysis_run_id"], "succeeded", source
                )
                run = await work.workflow.run(owner, operation["analysis_run_id"])
                envelope.update(analysisRun=run, applied=True)
            await work.llm.publish(operation, envelope)
            await work.commit()

    async def run(self):
        while not self.stopping.is_set():
            try:
                processed = await self.process_one()
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.getLogger("scope_guard").error("llm_worker_cycle_failed")
                processed = False
            if not processed:
                try:
                    await asyncio.wait_for(self.stopping.wait(), timeout=2)
                except TimeoutError:
                    pass
