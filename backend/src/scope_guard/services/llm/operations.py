"""Admission and read-only status. This service never calls a provider."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from scope_guard.domain.drafts.workflow import WorkflowError, empty_document
from scope_guard.domain.llm.runtime import PROMPT_VERSION, digest, encode
from scope_guard.services.drafts.workflow import context, expected, key

STAGES = {
    "check": ("analysis", "replies"),
    "agreement": ("change_order",),
    "translate": ("replies", "change_order"),
    "regenerate": ("reply",),
    "estimate": ("estimate",),
}


def operation_stages(kind):
    stages = STAGES[kind]
    return stages


def pending(row):
    return {
        "operationId": str(row["id"]),
        "status": row["status"],
        "statusUrl": "/api/v2/llm-operations/" + str(row["id"]),
        "deadlineAt": row["deadline_at"].isoformat(),
    }


class LlmOperations:
    def __init__(self, factory, store, policy, limiter=None, *, language_selector):
        self.factory, self.store, self.policy, self.limiter = factory, store, policy, limiter
        self.language_selector = language_selector

    async def admit(self, owner, identifier, kind, body):
        command = key(body)
        request_hash = digest({**body, "draftId": str(identifier), "kind": kind})
        # Lookup before checking a source revision that may have advanced after publication.
        async with self.factory() as work:
            draft = await work.workflow.draft(owner, identifier)
        prior = await self.store.prior(owner, UUID(draft["projectId"]), command, request_hash)
        if prior:
            return pending(prior)
        # Offline detector initialization/calibration can be slow; never hold row locks.
        selection, locale = await self.select_language(owner, draft, kind, body)
        async with self.factory() as work:
            project = await work.workflow.project(owner, UUID(draft["projectId"]), lock=True)
            draft = await work.workflow.draft(owner, identifier, lock=True)
            if project.get("archivedAt"):
                raise WorkflowError("projectArchived", 409)
            prior = await work.llm.prior(owner, UUID(project["id"]), command)
            if prior:
                if prior["request_hash"] != request_hash:
                    raise WorkflowError("operationMismatch", 409)
                return pending(prior)
            if int(draft["revision"]) != expected(body):
                raise WorkflowError("draftConflict", 409)
            if "_legacyRequest" in body:
                if (
                    body["_legacyRequest"] != draft["requestText"]
                    or body.get("_legacyProject") != draft["projectId"]
                ):
                    raise WorkflowError("analysisStale", 409)
                if (
                    kind == "regenerate"
                    and body.get("_legacyTone") != draft["draftDocument"]["reply"]["tone"]
                ):
                    raise WorkflowError("draftConflict", 409)
            if kind not in STAGES:
                raise WorkflowError("requestBodyInvalid")
            run = None
            if kind != "check":
                if not draft.get("lastAnalysisRunId"):
                    raise WorkflowError("analysisStale", 409)
                run = await work.workflow.run(owner, UUID(draft["lastAnalysisRunId"]))
                if run["status"] != "succeeded" or run["requestText"] != draft["requestText"]:
                    raise WorkflowError("analysisStale", 409)
            if not draft["requestText"].strip() or not project["scope"].strip():
                raise WorkflowError("requestBodyInvalid")
            timestamp = datetime.now(UTC)
            if kind in ("regenerate", "estimate") and draft["draftDocument"].get(
                "languageSelection"
            ):
                selection = deepcopy(draft["draftDocument"]["languageSelection"])
            frozen = {
                "project": context(project) if run is None else run["projectSnapshot"],
                "request": draft["requestText"],
                "locale": locale,
                "selection": selection,
                "document": empty_document(selection["selectedLanguage"])
                if kind == "check"
                else draft["draftDocument"],
                "analysis": run["resultSnapshot"] if run else None,
                "createdAt": timestamp.isoformat(),
                "sourceRevision": draft["revision"],
                "responseFormat": body.get("_responseFormat", "workflow"),
                "action": kind,
                "sourceAnalysisRunId": run["id"] if run else None,
            }
            if kind == "estimate":
                source = (await work.workflow.revision(owner, identifier, expected(body)))[
                    "stateSnapshot"
                ]
                commercial = source["context"]
                frozen["project"] = {
                    **frozen["project"],
                    **{
                        field: commercial.get(field)
                        for field in (
                            "pricingModel",
                            "currency",
                            "hourlyRate",
                            "fixedPrice",
                            "startDate",
                            "endDate",
                        )
                    },
                }
                order = draft["draftDocument"].get("changeOrder") or {}
                frozen["project"]["endDate"] = order.get("endDate") or commercial.get("endDate")
            if kind == "agreement":
                if draft["analysisIsStale"]:
                    raise WorkflowError("analysisStale", 409)
                # Serialize distinct concurrent clicks, not only redelivery of one key.
                inflight = await work.llm.active_agreement(owner, identifier)
                if inflight:
                    if inflight["source_revision"] != int(draft["revision"]):
                        raise WorkflowError("draftConflict", 409)
                    return pending(inflight)
                frozen["analysis"] = {
                    **frozen["analysis"],
                    **(frozen["analysis"].get("estimate") or {}),
                }
                frozen["prepareEstimate"] = (
                    frozen["document"].get("changeOrder") is None
                    and frozen["analysis"].get("hasAdditionalWork") is True
                    and any(
                        frozen["project"].get(f) != project.get(f)
                        for f in ("pricingModel", "hourlyRate", "fixedPrice", "currency")
                    )
                )
                if frozen["prepareEstimate"]:
                    frozen["project"] = {
                        **frozen["project"],
                        **{
                            f: project.get(f)
                            for f in ("pricingModel", "hourlyRate", "fixedPrice", "currency")
                        },
                    }
            selection["requestHash"] = digest(draft["requestText"])
            error = None
            if not self.policy.get("inputRate") or not self.policy.get("outputRate"):
                error = {"code": "errors.providerBudgetUnavailable", "status": 503}
            else:
                worst_call = (
                    Decimal(self.policy["inputRate"]) * 32768
                    + Decimal(self.policy["outputRate"]) * 4096
                )
                minimum = (
                    2 if kind in ("check", "translate") or frozen.get("prepareEstimate") else 1
                )
                if minimum * worst_call > Decimal(self.policy["maxCost"]):
                    error = {"code": "errors.providerBudgetUnavailable", "status": 503}
            if self.limiter and not self.limiter.allow(
                str(owner), int(timestamp.timestamp() * 1000)
            ):
                raise WorkflowError("analysisRateLimited", 429)
            if kind in ("check", "estimate"):
                run, _ = await work.workflow.create_run(
                    owner,
                    draft,
                    frozen["project"],
                    {
                        "locale": locale,
                        "documentLanguage": selection["selectedLanguage"],
                        "_model": self.policy["model"],
                        "_prompt": PROMPT_VERSION,
                        "kind": "estimate" if kind == "estimate" else "analysis",
                    },
                    command,
                    request_hash,
                )
            existing = kind == "agreement" and frozen["document"].get("changeOrder") is not None
            row = await work.llm.insert(
                {
                    "owner": owner,
                    "project": UUID(project["id"]),
                    "draft": identifier,
                    "revision": int(draft["revision"]),
                    "run": UUID(run["id"]),
                    "kind": kind,
                    "key": command,
                    "hash": request_hash,
                    "input": encode(frozen),
                    "input_hash": digest(frozen),
                    "policy": encode(
                        {
                            **self.policy,
                            "maxCalls": {
                                "check": 6,
                                "agreement": 6,
                                "translate": 8,
                                "regenerate": 6,
                                "estimate": 6,
                            }[kind],
                        }
                    ),
                    "status": "queued" if existing else "failed" if error else "queued",
                    "error": encode(error) if error else None,
                    "deadline": timestamp
                    + timedelta(seconds=self.policy.get("durationSeconds", 180)),
                    "finished": timestamp if error or existing else None,
                },
                tuple(
                    stage
                    for stage in (
                        ("estimate", "change_order")
                        if frozen.get("prepareEstimate")
                        else operation_stages(kind)
                    )
                    if stage != "change_order"
                    or kind != "translate"
                    or frozen["document"].get("changeOrder") is not None
                ),
            )
            if existing:
                await work.llm.restore_existing(row, {"draft": {**draft, "analysisRun": run}})
            if error and kind in ("check", "estimate"):
                await work.workflow.finish_run(owner, UUID(run["id"]), "running", None)
                await work.workflow.finish_run(
                    owner, UUID(run["id"]), "failed", None, "provider_budget_unavailable"
                )
            await work.commit()
        return pending(row)

    async def select_language(self, owner, draft, kind, body):
        if kind not in STAGES:
            raise WorkflowError("requestBodyInvalid")
        if kind == "check":
            locale, language = body.get("locale"), body.get("documentLanguage")
        else:
            if not draft.get("lastAnalysisRunId"):
                raise WorkflowError("analysisStale", 409)
            async with self.factory() as work:
                run = await work.workflow.run(owner, UUID(draft["lastAnalysisRunId"]))
            locale = run["interfaceLocale"]
            language = (
                body.get("language")
                if kind == "translate"
                else draft["draftDocument"]["reply"]["language"]
            )
        if locale not in ("ru", "en"):
            raise WorkflowError("localeInvalid")
        try:
            return await asyncio.to_thread(
                self.language_selector, draft["requestText"], locale, language
            ), locale
        except ValueError:
            raise WorkflowError("clientLanguageInvalid") from None

    async def status(self, owner, identifier):
        row = await self.store.get(owner, identifier)
        steps = await self.store.steps(identifier)
        return {
            **pending(row),
            "stages": {s["stage_key"]: s["status"] for s in steps},
            "responseFormat": row["frozen_input"].get("responseFormat", "workflow"),
            "result": row["result"],
            "error": row["error"],
        }
