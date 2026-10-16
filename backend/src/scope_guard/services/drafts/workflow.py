"""Persistent project/check workflows; model calls never hold a database UoW."""

import asyncio
import time
from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import UUID, uuid5

from scope_guard.domain.analysis.domain import (
    AnalysisInput,
    GenerationContext,
    MaterialInput,
    ReplyInput,
)
from scope_guard.domain.analysis.normalization import parse_snapshot
from scope_guard.domain.analysis.serialization import analysis_to_wire, materials_to_wire
from scope_guard.domain.drafts.workflow import (
    SAVE_REASONS,
    WorkflowError,
    analysis_matches,
    decimal_text,
    empty_document,
    operation_hash,
    validate_document,
)
from scope_guard.domain.projects.validation import parse_project

NAMESPACE = UUID("54954954-9549-4549-8549-549549549549")
CONTEXT_FIELDS = (
    "name",
    "clientName",
    "clientEmail",
    "industry",
    "scope",
    "startDate",
    "endDate",
    "pricingModel",
    "currency",
    "hourlyRate",
    "fixedPrice",
)


def key(body: dict) -> UUID:
    try:
        return UUID(body["operationId"])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise WorkflowError("operationRequired", 428) from None


def expected(body: dict) -> int:
    value = body.get("expectedRevision")
    if not isinstance(value, str) or not value.isdigit() or not 0 < int(value) < 2**63:
        raise WorkflowError("revisionRequired", 428)
    return int(value)


def context(project: dict) -> dict:
    return {name: project.get(name) for name in CONTEXT_FIELDS}


def generation_context(identifier: str, value: dict) -> GenerationContext:
    return GenerationContext(
        identifier,
        value["name"],
        value.get("clientName"),
        value["industry"],
        value["scope"],
        value.get("startDate"),
        value.get("pricingModel"),
        value.get("currency"),
        value.get("hourlyRate"),
        value.get("fixedPrice"),
    )


def active(project: dict):
    if project.get("archivedAt"):
        raise WorkflowError("projectArchived", 409)


def project_values(body: dict) -> dict:
    card = parse_project(body)
    values = {name: body.get(name) for name in CONTEXT_FIELDS}
    values.update(
        name=card.name,
        scope=card.scope.text,
        industry=str(card.industry),
        clientName=card.client.value,
    )
    for field in ("clientEmail", "endDate"):
        if values[field] is not None and not isinstance(values[field], str):
            raise WorkflowError("requestBodyInvalid")
    if values["endDate"]:
        try:
            date.fromisoformat(values["endDate"])
            if values["endDate"] < values["startDate"]:
                raise ValueError
        except ValueError:
            raise WorkflowError("endDateInvalid") from None
    for field in ("hourlyRate", "fixedPrice"):
        if field == ("hourlyRate" if values["pricingModel"] == "hourly" else "fixedPrice"):
            values[field] = decimal_text(str(body[field]), optional=False)
        else:
            values[field] = None
    return values


def formed_document(result: dict, project: dict, language: str, timestamp: str) -> dict:
    document = empty_document(language)
    document["reply"].update(text=result["replies"]["neutral"], generated=result["replies"])
    if result["verdict"] != "in_scope" and result.get(
        "hasAdditionalWork", result["verdict"] == "out_of_scope"
    ):
        co = result["changeOrder"]
        try:
            cost = decimal_text(str(co.get("additionalCost", ""))) or ""
            hours = decimal_text(str(co.get("estimatedHours", ""))) or ""
        except WorkflowError:
            cost, hours = "", ""
        editor = {
            "description": co.get("description", ""),
            "estimatedHours": hours,
            "additionalCost": cost,
            "currency": co.get("currency") or project.get("currency") or "",
            "timelineImpact": co.get("timelineImpact", ""),
            "rationale": co.get("rationale", ""),
            "note": co.get("note", ""),
            "language": language,
            "createdAt": timestamp,
            "projectName": project["name"],
            "providerName": "",
            "clientName": project.get("clientName") or "",
            "clientEmail": project.get("clientEmail") or "",
            "endDate": project.get("endDate") or "",
            "additionalTerms": "",
            "clientApproverName": "",
            "approvalDate": "",
            "noAdditionalCharge": False,
        }
        editor["aiValues"] = {
            name: editor[name]
            for name in (
                "description",
                "estimatedHours",
                "additionalCost",
                "currency",
                "timelineImpact",
                "rationale",
                "note",
            )
        }
        if result.get("changeOrderLabels"):
            editor["changeOrderLabels"] = result["changeOrderLabels"]
        document["changeOrder"] = editor
    return validate_document(document)


class WorkflowService:
    def __init__(self, factory, generator=None, limiter=None, storage=None):
        self.factory, self.generator, self.limiter, self.storage = (
            factory,
            generator,
            limiter,
            storage,
        )

    async def enrich(self, owner, draft):
        if draft.get("lastAnalysisRunId"):
            async with self.factory() as work:
                run = await work.workflow.run(owner, UUID(draft["lastAnalysisRunId"]))
            return {**draft, "analysisRun": run}
        return {**draft, "analysisRun": None}

    async def projects(self, owner, archived=False):
        async with self.factory() as work:
            projects = await work.workflow.projects(owner, archived)
            for project in projects:
                project["history"] = await work.workflow.histories(owner, UUID(project["id"]))
            return projects

    async def project(self, owner, identifier):
        async with self.factory() as work:
            project = await work.workflow.project(owner, identifier)
            project["history"] = await work.workflow.histories(owner, identifier)
            return project

    async def create_project(self, owner, body):
        values = project_values(body)
        async with self.factory() as work:
            project = await work.workflow.create_project(
                owner, values, key(body), operation_hash(values)
            )
            await work.commit()
        return {**project, "history": []}

    async def project_draft(self, owner, identifier):
        async with self.factory() as work:
            draft = await work.workflow.project_draft(owner, identifier)
        return await self.enrich(owner, draft)

    async def draft(self, owner, identifier):
        async with self.factory() as work:
            draft = await work.workflow.draft(owner, identifier)
        return await self.enrich(owner, draft)

    async def save(self, owner, identifier, body):
        changes = body.get("changes")
        if not isinstance(changes, dict) or changes.keys() - {"requestText", "draftDocument"}:
            raise WorkflowError("requestBodyInvalid")
        reason = body.get("reason", "autosave")
        if reason not in {
            "autosave",
            "manual_save",
            "tone_change",
            "language_change",
            "change_order_edit",
        }:
            raise WorkflowError("requestBodyInvalid")
        return await self.write(owner, identifier, body, changes, reason)

    async def write(self, owner, identifier, body, changes, reason, *, trusted=False):
        operation, revision, digest = key(body), expected(body), operation_hash(body)
        if reason not in SAVE_REASONS:
            raise WorkflowError("requestBodyInvalid")
        async with self.factory() as work:
            prior = await work.workflow.saved_operation(owner, identifier, operation, digest)
            if prior:
                return await self.enrich(owner, prior)
            draft = await work.workflow.draft(owner, identifier, lock=True)
            project = await work.workflow.project(owner, UUID(draft["projectId"]))
            active(project)
            if int(draft["revision"]) != revision:
                raise WorkflowError("draftConflict", 409)
            if "requestText" in changes and not trusted:
                if (
                    not isinstance(changes["requestText"], str)
                    or len(changes["requestText"]) > 100_000
                ):
                    raise WorkflowError("requestBodyInvalid")
                changes = {
                    **changes,
                    "analysisIsStale": changes["requestText"] != draft["requestText"]
                    or draft["analysisIsStale"],
                }
            if "draftDocument" in changes:
                document = validate_document(changes["draftDocument"])
                if not trusted and document.get("languageSelection") != draft["draftDocument"].get(
                    "languageSelection"
                ):
                    raise WorkflowError("documentInvalid")
                if (
                    not trusted
                    and document["reply"]["language"] != draft["draftDocument"]["reply"]["language"]
                ):
                    raise WorkflowError("documentInvalid")
                if (
                    not trusted
                    and changes.get("requestText", draft["requestText"]) != draft["requestText"]
                ):
                    if document.get("languageSelection"):
                        document = deepcopy(document)
                        document["languageSelection"]["override"] = False
                if (
                    not trusted
                    and document["reply"]["generated"]
                    != draft["draftDocument"]["reply"]["generated"]
                ):
                    raise WorkflowError("documentInvalid")
                if not trusted:
                    if document.get("estimate") != draft["draftDocument"].get("estimate"):
                        raise WorkflowError("documentInvalid")
                    previous_order = draft["draftDocument"].get("changeOrder") or {}
                    proposed_order = document.get("changeOrder") or {}
                    if proposed_order.get("aiValues", {}) != previous_order.get("aiValues", {}):
                        raise WorkflowError("documentInvalid")
                changes = {**changes, "draftDocument": document}
            elif changes.get("requestText", draft["requestText"]) != draft["requestText"]:
                document = deepcopy(draft["draftDocument"])
                if document.get("languageSelection"):
                    document["languageSelection"]["override"] = False
                changes = {**changes, "draftDocument": document}
            result = await work.workflow.save(
                owner, identifier, revision, operation, digest, changes, reason, context(project)
            )
            await work.commit()
        return await self.enrich(owner, result)

    async def clear(self, owner, identifier, body):
        draft = await self.draft(owner, identifier)
        return await self.write(
            owner,
            identifier,
            body,
            {
                "requestText": "",
                "lastAnalysisRunId": None,
                "analysisIsStale": True,
                "draftDocument": empty_document(draft["draftDocument"]["reply"]["language"]),
            },
            "clear",
            trusted=True,
        )

    async def revisions(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.revisions(owner, identifier)

    async def legacy_revision(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.legacy_revision(owner, identifier)

    async def restore(self, owner, identifier, number, body):
        async with self.factory() as work:
            saved = (await work.workflow.revision(owner, identifier, number))["stateSnapshot"]
            current = await work.workflow.draft(owner, identifier)
            project = await work.workflow.project(owner, UUID(current["projectId"]))
            run = (
                await work.workflow.run(owner, UUID(saved["lastAnalysisRunId"]))
                if saved.get("lastAnalysisRunId")
                else None
            )
        parameters = {**body, "restoredRevision": str(number)}
        return await self.write(
            owner,
            identifier,
            parameters,
            {
                "requestText": saved["requestText"],
                "draftDocument": saved["draftDocument"],
                "lastAnalysisRunId": saved.get("lastAnalysisRunId"),
                "analysisIsStale": not analysis_matches(
                    run, saved["requestText"], context(project)
                ),
            },
            "restore",
            trusted=True,
        )

    async def reopen_history(self, owner, identifier, body):
        entry = await self.history(owner, identifier)
        snapshot = entry["checkSnapshot"]
        if entry["sourceKind"] != "explicit" or not entry.get("analysisRunId"):
            raise WorkflowError("legacyProvenanceMissing", 409)
        run = await self.run(owner, UUID(entry["analysisRunId"]))
        draft = await self.project_draft(owner, UUID(entry["projectId"]))
        project = await self.project(owner, UUID(entry["projectId"]))
        return await self.write(
            owner,
            UUID(draft["id"]),
            {**body, "historyEntryId": str(identifier)},
            {
                "requestText": snapshot["requestText"],
                "draftDocument": snapshot["draftDocument"],
                "lastAnalysisRunId": run["id"],
                "analysisIsStale": not analysis_matches(
                    run, snapshot["requestText"], context(project)
                ),
            },
            "restore",
            trusted=True,
        )

    async def update_project(self, owner, identifier, body):
        values = project_values(body)
        async with self.factory() as work:
            previous = await work.workflow.project(owner, identifier, lock=True)
            active(previous)
            draft = await work.workflow.project_draft(owner, identifier)
            digest = operation_hash(body)
            prior = await work.workflow.saved_operation(owner, UUID(draft["id"]), key(body), digest)
            if prior:
                return previous
            if int(draft["revision"]) != expected(body):
                raise WorkflowError("draftConflict", 409)
            project = await work.workflow.update_project(owner, identifier, values)
            stale = context(previous) != context(project) or draft["analysisIsStale"]
            await work.workflow.save(
                owner,
                UUID(draft["id"]),
                expected(body),
                key(body),
                digest,
                {"analysisIsStale": stale},
                "project_change",
                context(project),
            )
            await work.commit()
        return {**project, "history": await self.histories(owner, identifier)}

    async def archive_project(self, owner, identifier):
        async with self.factory() as work:
            await work.workflow.update_project(owner, identifier, {"archived": True})
            await work.commit()

    def allowance(self, owner):
        if self.limiter and not self.limiter.allow(str(owner), int(time.time() * 1000)):
            raise WorkflowError("analysisRateLimited", 429)

    async def run(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.run(owner, identifier)

    async def analyze(self, owner, identifier, body):
        parameters = {**body, "draftId": str(identifier)}
        operation, revision, digest = key(body), expected(body), operation_hash(parameters)
        if body.get("locale") not in ("en", "ru"):
            raise WorkflowError("localeInvalid")
        async with self.factory() as work:
            draft = await work.workflow.draft(owner, identifier, lock=True)
            project = await work.workflow.project(owner, UUID(draft["projectId"]))
            active(project)
            # Repository checks existing operation before validating the current revision.
            source = {**draft, "revision": str(revision)}
            frozen_context = context(project)
            if body.get("kind") == "estimate":
                source = (await work.workflow.revision(owner, identifier, revision))[
                    "stateSnapshot"
                ]
                frozen_context = context(source["context"])
                editor = source["draftDocument"].get("changeOrder") or {}
                frozen_context["estimateEndDate"] = (
                    editor.get("endDate") or frozen_context.get("endDate") or None
                )
            run, created = await work.workflow.create_run(
                owner, source, frozen_context, parameters, operation, digest
            )
            if created:
                if not draft["requestText"].strip() or not project["scope"].strip():
                    raise WorkflowError("requestBodyInvalid")
                self.allowance(owner)
                await work.workflow.finish_run(owner, UUID(run["id"]), "running", None)
            await work.commit()
        if not created:
            if run["status"] != "succeeded":
                return {"analysisRun": run, "draft": None, "applied": False}
            return await self.apply_analysis(owner, UUID(run["id"]))
        try:
            timestamp = datetime.now(UTC).isoformat()
            effective_deadline = run["projectSnapshot"].get(
                "estimateEndDate", run["projectSnapshot"].get("endDate")
            )
            result = await self.generator.analyze(
                AnalysisInput(
                    generation_context(draft["projectId"], run["projectSnapshot"]),
                    run["requestText"],
                    run["interfaceLocale"],
                    effective_deadline,
                    timestamp,
                    run["requestedDocumentLanguage"],
                )
            )
            result_wire = analysis_to_wire(result)
            from scope_guard.domain.change_orders.estimation import commercial_signature

            result_wire["commercialSignature"] = commercial_signature(
                generation_context(draft["projectId"], run["projectSnapshot"]),
                effective_deadline,
            )
            result_wire["draftCreatedAt"] = timestamp
            if result_wire.get("hasAdditionalWork") and result_wire["changeOrder"].get(
                "currency"
            ) != run["projectSnapshot"].get("currency"):
                result_wire["estimateValid"] = False
        except BaseException as error:
            cancelled = isinstance(error, asyncio.CancelledError)

            async def record_failure():
                async with self.factory() as work:
                    await work.workflow.finish_run(
                        owner,
                        UUID(run["id"]),
                        "cancelled" if cancelled else "failed",
                        None,
                        "generation_cancelled" if cancelled else "generation_failed",
                    )
                    await work.commit()

            await asyncio.shield(record_failure())
            raise
        async with self.factory() as work:
            await work.workflow.finish_run(owner, UUID(run["id"]), "succeeded", result_wire)
            await work.commit()
        return await self.apply_analysis(owner, UUID(run["id"]))

    async def apply_analysis(self, owner, identifier):
        run = await self.run(owner, identifier)
        if run["status"] != "succeeded":
            raise WorkflowError("analysisNotReady", 409)
        operation = uuid5(NAMESPACE, str(identifier) + ":apply")
        body = {
            "expectedRevision": run["sourceDraftRevision"],
            "operationId": str(operation),
            "analysisRunId": str(identifier),
        }
        document = formed_document(
            run["resultSnapshot"],
            run["projectSnapshot"],
            run["resultSnapshot"].get("clientLanguage")
            or run["requestedDocumentLanguage"]
            or run["interfaceLocale"],
            run["finishedAt"],
        )
        analysis_reference = str(identifier)
        if run.get("purpose") == "estimate":
            if (
                run["resultSnapshot"]["verdict"] == "in_scope"
                or run["resultSnapshot"].get("estimateValid") is not True
            ):
                raise WorkflowError("analysisInvalid", 409)
            async with self.factory() as work:
                source = (
                    await work.workflow.revision(
                        owner, UUID(run["sourceDraftId"]), int(run["sourceDraftRevision"])
                    )
                )["stateSnapshot"]
            proposed = document["changeOrder"]
            document = deepcopy(source["draftDocument"])
            analysis_reference = source.get("lastAnalysisRunId")
            old = document["changeOrder"]
            if old and proposed:
                from scope_guard.domain.change_orders.merge import merge_estimate

                document["changeOrder"] = merge_estimate(old, proposed["aiValues"])
            else:
                document["changeOrder"] = proposed
            document["estimate"] = {
                "analysisRunId": str(identifier),
                "sourceDraftRevision": run["sourceDraftRevision"],
                "effectiveEndDate": run["projectSnapshot"].get(
                    "estimateEndDate", run["projectSnapshot"].get("endDate")
                ),
                "commercialSignature": run["resultSnapshot"]["commercialSignature"],
                "estimateValid": run["resultSnapshot"]["estimateValid"],
            }
        try:
            result = await self.write(
                owner,
                UUID(run["sourceDraftId"]),
                body,
                {
                    "lastAnalysisRunId": analysis_reference,
                    "analysisIsStale": False,
                    "draftDocument": document,
                },
                "analysis_apply",
                trusted=True,
            )
            return {"analysisRun": run, "draft": result, "applied": True}
        except WorkflowError as error:
            if error.code != "errors.draftConflict":
                raise
            return {"analysisRun": run, "draft": None, "applied": False, "conflict": True}

    async def estimate(self, owner, identifier, body):
        async with self.factory() as work:
            source = (await work.workflow.revision(owner, identifier, expected(body)))[
                "stateSnapshot"
            ]
            if not source.get("lastAnalysisRunId") or source.get("analysisIsStale"):
                raise WorkflowError("analysisStale", 409)
            run = await work.workflow.run(owner, UUID(source["lastAnalysisRunId"]))
        return await self.analyze(
            owner,
            identifier,
            {
                **body,
                "kind": "estimate",
                "locale": run["interfaceLocale"],
                "documentLanguage": source["draftDocument"]["reply"]["language"],
            },
        )

    async def generate(self, owner, identifier, kind, body):
        operation, revision, digest = (
            key(body),
            expected(body),
            operation_hash({**body, "kind": kind}),
        )
        async with self.factory() as work:
            prior = await work.workflow.saved_operation(owner, identifier, operation, digest)
            if prior:
                return await self.enrich(owner, prior)
            draft = await work.workflow.draft(owner, identifier)
            project = await work.workflow.project(owner, UUID(draft["projectId"]))
            active(project)
            if int(draft["revision"]) != revision:
                raise WorkflowError("draftConflict", 409)
            run = (
                await work.workflow.run(owner, UUID(draft["lastAnalysisRunId"]))
                if draft["lastAnalysisRunId"]
                else None
            )
            if draft["analysisIsStale"] or not analysis_matches(
                run, draft["requestText"], context(project)
            ):
                raise WorkflowError("analysisStale", 409)
        self.allowance(owner)
        document = deepcopy(draft["draftDocument"])
        reply = document["reply"]
        frozen = generation_context(draft["projectId"], run["projectSnapshot"])
        if kind == "regenerate":
            text = await self.generator.regenerate_reply(
                ReplyInput(
                    frozen,
                    run["requestText"],
                    run["interfaceLocale"],
                    reply["tone"],
                    reply["text"],
                    reply["language"],
                )
            )
            reply["text"] = text
            reply["generated"][reply["tone"]] = text
        elif kind == "translate":
            language = body.get("language")
            from scope_guard.domain.shared.language import normalize_language

            language = normalize_language(language)
            if not language:
                raise WorkflowError("clientLanguageInvalid")
            material_source = deepcopy(run["resultSnapshot"])
            material_source["replies"] = {**reply["generated"], reply["tone"]: reply["text"]}
            if document["changeOrder"]:
                for field in (
                    "description",
                    "timelineImpact",
                    "rationale",
                    "note",
                    "additionalCost",
                ):
                    material_source["changeOrder"][field] = document["changeOrder"].get(field, "")
            value = await self.generator.translate_materials(
                MaterialInput(
                    frozen,
                    run["requestText"],
                    run["interfaceLocale"],
                    language,
                    parse_snapshot(material_source, run["interfaceLocale"]),
                )
            )
            material = materials_to_wire(value)
            reply.update(
                language=language,
                generated=material["replies"],
                text=material["replies"][reply["tone"]],
            )
            if document["changeOrder"] and material.get("changeOrder"):
                document["changeOrder"].update(material["changeOrder"])
                document["changeOrder"]["language"] = language
                if material.get("changeOrderLabels"):
                    document["changeOrder"]["changeOrderLabels"] = material["changeOrderLabels"]
        else:
            raise WorkflowError("requestBodyInvalid")
        # The operation hash includes kind, while the public body keeps the same key.
        return await self.write(
            owner,
            identifier,
            {**body, "kind": kind},
            {"draftDocument": document},
            "regenerate" if kind == "regenerate" else "language_change",
            trusted=True,
        )

    async def histories(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.histories(owner, identifier)

    async def history(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.history(owner, identifier)

    async def complete(self, owner, identifier, body):
        operation, revision, digest = key(body), expected(body), operation_hash(body)
        async with self.factory() as work:
            draft = await work.workflow.draft(owner, identifier, lock=True)
            project_id = UUID(draft["projectId"])
            prior = await work.workflow.history_operation(owner, project_id, operation, digest)
            if prior:
                return prior
            project = await work.workflow.project(owner, project_id)
            active(project)
            if int(draft["revision"]) != revision:
                raise WorkflowError("draftConflict", 409)
            run = (
                await work.workflow.run(owner, UUID(draft["lastAnalysisRunId"]))
                if draft["lastAnalysisRunId"]
                else None
            )
            if draft["analysisIsStale"] or not analysis_matches(
                run, draft["requestText"], context(project)
            ):
                raise WorkflowError("analysisStale", 409)
            result = await work.workflow.complete(
                owner, draft, context(project), run, operation, digest
            )
            await work.commit()
            return result

    async def finalize(self, owner, identifier, body):
        async with self.factory() as work:
            history = await work.workflow.history(owner, identifier)
            active(await work.workflow.project(owner, UUID(history["projectId"])))
            result = await work.workflow.finalize(owner, history, key(body), operation_hash(body))
            await work.commit()
            return result

    async def agreement(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.agreement(owner, identifier)

    async def agreements(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.agreements(owner, identifier)

    async def void(self, owner, identifier, body):
        async with self.factory() as work:
            result = await work.workflow.void(
                owner,
                identifier,
                expected(body),
                key(body),
                operation_hash({**body, "agreementId": str(identifier)}),
            )
            await work.commit()
            return result

    async def export(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.export(owner, identifier)

    async def exports(self, owner, identifier):
        async with self.factory() as work:
            return await work.workflow.exports(owner, identifier)

    async def create_export(self, owner, identifier, body):
        async with self.factory() as work:
            agreement = await work.workflow.agreement(owner, identifier)
            active(await work.workflow.project(owner, UUID(agreement["projectId"])))
            if self.storage is None:
                raise WorkflowError("exportStorageUnavailable", 503)
            if (
                body.get("language", agreement["contentSnapshot"]["document"]["language"])
                != agreement["contentSnapshot"]["document"]["language"]
            ):
                raise WorkflowError("documentLanguageMismatch", 409)
            result = await work.workflow.create_export(
                owner, agreement, key(body), operation_hash(body)
            )
            await work.commit()
            return result

    async def retry_export(self, owner, identifier, body):
        async with self.factory() as work:
            result = await work.workflow.retry_export(
                owner, identifier, key(body), operation_hash({**body, "exportId": str(identifier)})
            )
            await work.commit()
            return result

    async def download(self, owner, identifier):
        metadata = await self.export(owner, identifier)
        if metadata["status"] != "ready":
            raise WorkflowError("exportNotReady", 409)
        if self.storage is None:
            raise WorkflowError("exportStorageUnavailable", 503)
        data = await self.storage.get(metadata["objectKey"])
        import hashlib

        if hashlib.sha256(data).hexdigest() != metadata["checksum"]:
            raise WorkflowError("exportIntegrityFailed", 503)
        return data

    async def evaluate(self, owner, identifier, body):
        async with self.factory() as work:
            run = await work.workflow.run(owner, identifier)
            if run["status"] != "succeeded":
                raise WorkflowError("analysisNotReady", 409)
            result = await work.workflow.evaluate(owner, run, body)
            await work.commit()
            return result
