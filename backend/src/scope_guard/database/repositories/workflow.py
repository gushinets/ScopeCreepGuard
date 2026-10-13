"""Owned SQLAlchemy workflow repository. The enclosing UoW owns every transaction."""

import json
from uuid import UUID, uuid4, uuid5

from sqlalchemy import text

from scope_guard.domain.drafts.workflow import DraftState, WorkflowError, empty_document
from scope_guard.domain.drafts.workflow_repository import WorkflowRepository

NAMESPACE = UUID("54954954-9549-4549-8549-549549549549")


def detached(value: dict) -> dict:
    result = {}
    for key, item in value.items():
        parts = key.split("_")
        name = parts[0] + "".join(part.title() for part in parts[1:])
        if key == "client":
            name = "clientName"
        if key in ("revision", "source_draft_revision") and item is not None:
            item = str(item)
        result[name] = item
    return result


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


class WorkflowSQLRepository:
    def __init__(self, session):
        self.session = session

    async def one(self, sql: str, parameters: dict | None = None) -> dict | None:
        value = await self.session.scalar(text(sql), parameters or {})
        return detached(value) if value is not None else None

    async def many(self, sql: str, parameters: dict) -> list[dict]:
        values = (await self.session.execute(text(sql), parameters)).scalars().all()
        return [detached(value) for value in values]

    async def project(self, owner: UUID, identifier: UUID, *, lock=False) -> dict:
        value = await self.one(
            (
                "SELECT to_jsonb(p)||jsonb_build_object('hourly_rate',p.hourly_rate::text"
                ",'fixed_price',p.fixed_price::text) FROM projects p WHERE p.id=:id AND p"
                ".user_id=:owner"
            )
            + (" FOR UPDATE" if lock else ""),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("projectNotFound", 404)
        return value

    async def projects(self, owner: UUID, archived=False) -> list[dict]:
        return await self.many(
            (
                "SELECT to_jsonb(p)||jsonb_build_object('hourly_rate',p.hourly_rate::text"
                ",'fixed_price',p.fixed_price::text) FROM projects p WHERE user_id=:owner"
                " AND (archived_at IS NOT NULL)=:archived ORDER BY created_at DESC,id"
            ),
            {"owner": owner, "archived": archived},
        )

    async def event(self, project, operation, event, owner=None, payload=None, **links):
        names = {
            "draft_id",
            "draft_revision_id",
            "analysis_run_id",
            "history_entry_id",
            "change_order_id",
            "document_export_id",
        }
        if links.keys() - names:
            raise ValueError("invalid_event_links")
        columns = ",".join(links)
        values = ",".join(":" + key for key in links)
        await self.session.execute(
            text(
                (
                    "INSERT INTO activity_events(project_id,operation_id,event_type,actor_typ"
                    "e,actor_user_id,payload,payload_version"
                )
                + ("," + columns if columns else "")
                + ") VALUES(:project,:operation,:event,:actor,:owner,CAST(:payload AS jsonb),1"
                + ("," + values if values else "")
                + ") ON CONFLICT(project_id,operation_id,event_type) DO NOTHING"
            ),
            {
                "project": project,
                "operation": operation,
                "event": event,
                "actor": "user" if owner else "system",
                "owner": owner,
                "payload": encoded(payload or {}),
                **links,
            },
        )

    async def create_project(self, owner, values, key, digest):
        await self.session.execute(
            text("SELECT id FROM users WHERE id=:owner FOR UPDATE"), {"owner": owner}
        )
        prior = await self.one(
            "SELECT to_jsonb(p) FROM projects p WHERE user_id=:owner AND creation_key=:key",
            {"owner": owner, "key": key},
        )
        if prior:
            if prior["creationRequestHash"] != digest:
                raise WorkflowError("operationMismatch", 409)
            return await self.project(owner, UUID(prior["id"]))
        p = await self.one(
            (
                "INSERT INTO projects(user_id,name,client,client_email,industry,scope,sta"
                "rt_date,end_date,pricing_model,currency,hourly_rate,fixed_price,updated_"
                "at,creation_key,creation_request_hash) VALUES(:owner,:name,:clientName,:"
                "clientEmail,:industry,:scope,:startDate,:endDate,:pricingModel,:currency"
                ",:hourlyRate,:fixedPrice,now(),:key,:hash) RETURNING to_jsonb(projects)"
            ),
            {**values, "owner": owner, "key": key, "hash": digest},
        )
        project = UUID(p["id"])
        draft = await self.one(
            (
                "INSERT INTO drafts(project_id,request_text,analysis_is_stale,draft_docum"
                "ent,revision) VALUES(:project,'',true,CAST(:doc AS jsonb),1) RETURNING t"
                "o_jsonb(drafts)"
            ),
            {"project": project, "doc": encoded(empty_document())},
        )
        context = await self.project(owner, project)
        await self.insert_revision(draft, key, digest, "initial", owner, context)
        return context

    async def update_project(self, owner, identifier, values):
        await self.project(owner, identifier, lock=True)
        if values == {"archived": True}:
            await self.session.execute(
                text(
                    "UPDATE projects SET archived_at=COALESCE(archived_at,now()),updated_at=n"
                    "ow() WHERE id=:id AND user_id=:owner"
                ),
                {"id": identifier, "owner": owner},
            )
        else:
            await self.session.execute(
                text(
                    "UPDATE projects SET name=:name,client=:clientName,client_email=:clientEm"
                    "ail,industry=:industry,scope=:scope,start_date=:startDate,end_date=:endD"
                    "ate,pricing_model=:pricingModel,currency=:currency,hourly_rate=:hourlyRa"
                    "te,fixed_price=:fixedPrice,updated_at=now() WHERE id=:id AND user_id=:ow"
                    "ner"
                ),
                {**values, "id": identifier, "owner": owner},
            )
        return await self.project(owner, identifier)

    async def draft(self, owner, identifier, *, lock=False):
        if lock:
            found = await self.one(
                (
                    "SELECT jsonb_build_object('project_id',d.project_id) FROM drafts d JOIN "
                    "projects p ON p.id=d.project_id WHERE d.id=:id AND p.user_id=:owner"
                ),
                {"id": identifier, "owner": owner},
            )
            if found:
                await self.project(owner, UUID(found["projectId"]), lock=True)
        value = await self.one(
            (
                "SELECT to_jsonb(d) FROM drafts d JOIN projects p ON p.id=d.project_id WH"
                "ERE d.id=:id AND p.user_id=:owner AND d.revision IS NOT NULL"
            )
            + (" FOR UPDATE OF d" if lock else ""),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("draftNotFound", 404)
        return value

    async def project_draft(self, owner, project):
        await self.project(owner, project)
        value = await self.one(
            "SELECT to_jsonb(d) FROM drafts d WHERE project_id=:project AND revision IS NOT NULL",
            {"project": project},
        )
        if not value:
            raise WorkflowError("draftNotFound", 404)
        return value

    async def saved_operation(self, owner, draft, operation, digest):
        await self.draft(owner, draft)
        row = await self.one(
            (
                "SELECT to_jsonb(r) FROM draft_revisions r WHERE draft_id=:draft AND oper"
                "ation_id=:op"
            ),
            {"draft": draft, "op": operation},
        )
        if row and row["requestHash"] != digest:
            raise WorkflowError("operationMismatch", 409)
        return row["stateSnapshot"] if row else None

    async def insert_revision(
        self, draft, operation, digest, reason, owner, context, changed_fields=None
    ):
        snapshot = {
            key: draft[key]
            for key in (
                "id",
                "projectId",
                "requestText",
                "lastAnalysisRunId",
                "analysisIsStale",
                "draftDocument",
                "revision",
                "createdAt",
                "updatedAt",
            )
        }
        snapshot.update(version=2, context=context)
        revision_id = uuid4()
        await self.session.execute(
            text(
                "INSERT INTO draft_revisions(id,draft_id,project_id,revision,state_snapsh"
                "ot,schema_version,reason,actor_type,actor_user_id,operation_id,request_h"
                "ash) VALUES(:id,:draft,:project,:revision,CAST(:snapshot AS jsonb),2,:re"
                "ason,'user',:owner,:op,:hash)"
            ),
            {
                "id": revision_id,
                "draft": draft["id"],
                "project": draft["projectId"],
                "revision": int(draft["revision"]),
                "snapshot": encoded(snapshot),
                "reason": reason,
                "owner": owner,
                "op": operation,
                "hash": digest,
            },
        )
        await self.event(
            draft["projectId"],
            operation,
            reason,
            owner,
            {"revision": draft["revision"], "changedFields": changed_fields or []},
            draft_id=draft["id"],
            draft_revision_id=revision_id,
        )
        return snapshot

    async def save(self, owner, identifier, expected, operation, digest, changes, reason, context):
        prior = await self.saved_operation(owner, identifier, operation, digest)
        if prior:
            return prior
        current = await self.draft(owner, identifier, lock=True)
        prior = await self.saved_operation(owner, identifier, operation, digest)
        if prior:
            return prior
        if int(current["revision"]) != expected:
            raise WorkflowError("draftConflict", 409)
        updated = {
            **current,
            **DraftState.from_snapshot(current)
            .apply(expected, changes, restored_analysis_validated=reason == "restore")
            .snapshot(),
        }
        row = await self.one(
            (
                "UPDATE drafts SET request_text=:request,draft_document=CAST(:doc AS json"
                "b),last_analysis_run_id=:run,analysis_is_stale=:stale,revision=revision+"
                "1,updated_at=now() WHERE id=:id AND revision=:expected RETURNING to_json"
                "b(drafts)"
            ),
            {
                "request": updated["requestText"],
                "doc": encoded(updated["draftDocument"]),
                "run": updated["lastAnalysisRunId"],
                "stale": updated["analysisIsStale"],
                "id": identifier,
                "expected": expected,
            },
        )
        if row is None:
            raise WorkflowError("draftConflict", 409)
        changed_fields = [
            name
            for name in ("requestText", "lastAnalysisRunId", "analysisIsStale")
            if current[name] != row[name]
        ]
        previous_doc, next_doc = current["draftDocument"], row["draftDocument"]
        for name in ("text", "tone", "language", "generated"):
            if previous_doc["reply"].get(name) != next_doc["reply"].get(name):
                changed_fields.append("reply." + name)
        if previous_doc["changeOrder"] is None or next_doc["changeOrder"] is None:
            if previous_doc["changeOrder"] != next_doc["changeOrder"]:
                changed_fields.append("changeOrder")
        else:
            changed_fields.extend(
                "changeOrder." + name
                for name in sorted(
                    previous_doc["changeOrder"].keys() | next_doc["changeOrder"].keys()
                )
                if previous_doc["changeOrder"].get(name) != next_doc["changeOrder"].get(name)
            )
        return await self.insert_revision(
            row, operation, digest, reason, owner, context, changed_fields
        )

    async def revisions(self, owner, draft):
        await self.draft(owner, draft)
        return await self.many(
            (
                "SELECT to_jsonb(r) FROM draft_revisions r WHERE draft_id=:draft ORDER BY"
                " revision DESC"
            ),
            {"draft": draft},
        )

    async def legacy_revision(self, owner, identifier):
        value = await self.one(
            "SELECT to_jsonb(r) FROM draft_revisions r JOIN projects p ON p.id=r.project_id "
            "WHERE r.id=:id AND r.reason='legacy_import' AND p.user_id=:owner",
            {"id": identifier, "owner": owner},
        )
        if value is None:
            raise WorkflowError("revisionNotFound", 404)
        return value

    async def ready_exports_before(self, cutoff):
        return await self.many(
            "SELECT to_jsonb(e) FROM document_exports e WHERE status='ready' AND created_at"
            "<:cutoff",
            {"cutoff": cutoff},
        )

    async def expire_export(self, identifier, cutoff):
        row = await self.one(
            "UPDATE document_exports SET status='expired' WHERE id=:id AND status='ready' "
            "AND created_at<:cutoff RETURNING to_jsonb(document_exports)",
            {"id": identifier, "cutoff": cutoff},
        )
        if row:
            await self.event(
                row["projectId"],
                uuid5(NAMESPACE, row["id"] + ":expiry"),
                "export_expired",
                document_export_id=identifier,
            )
        return row is not None

    async def revision(self, owner, draft, number):
        await self.draft(owner, draft)
        value = await self.one(
            (
                "SELECT to_jsonb(r) FROM draft_revisions r WHERE draft_id=:draft AND revi"
                "sion=:revision"
            ),
            {"draft": draft, "revision": number},
        )
        if value is None:
            raise WorkflowError("revisionNotFound", 404)
        return value

    async def create_run(self, owner, draft, context, parameters, key, digest):
        await self.project(owner, UUID(draft["projectId"]), lock=True)
        prior = await self.one(
            (
                "SELECT to_jsonb(r) FROM analysis_runs r WHERE project_id=:project AND id"
                "empotency_key=:key"
            ),
            {"project": draft["projectId"], "key": key},
        )
        if prior:
            if prior["requestHash"] != digest:
                raise WorkflowError("operationMismatch", 409)
            return prior, False
        current = await self.draft(owner, UUID(draft["id"]), lock=True)
        if current["revision"] != draft["revision"]:
            raise WorkflowError("draftConflict", 409)
        run = await self.one(
            (
                "INSERT INTO analysis_runs(project_id,source_draft_id,source_draft_revisi"
                "on,requested_by_user_id,request_text,project_snapshot,interface_locale,r"
                "equested_document_language,input_schema_version,status,model,prompt_vers"
                "ion,idempotency_key,request_hash) VALUES(:project,:draft,:revision,:owne"
                "r,:request,CAST(:snapshot AS jsonb),:locale,:language,1,'pending','gpt-5"
                ".4-nano',:prompt,:key,:hash) RETURNING to_jsonb(analysis_runs)"
            ),
            {
                "project": draft["projectId"],
                "draft": draft["id"],
                "revision": int(draft["revision"]),
                "owner": owner,
                "request": draft["requestText"],
                "snapshot": encoded(context),
                "locale": parameters["locale"],
                "language": parameters.get("documentLanguage"),
                "prompt": "analysis-v1",
                "key": key,
                "hash": digest,
            },
        )
        await self.event(
            draft["projectId"],
            key,
            "analysis_created",
            owner,
            {"sourceRevision": draft["revision"], "purpose": parameters.get("kind", "analysis")},
            analysis_run_id=run["id"],
            draft_id=draft["id"],
        )
        run["purpose"] = parameters.get("kind", "analysis")
        return run, True

    async def run(self, owner, identifier):
        value = await self.one(
            (
                "SELECT to_jsonb(r) FROM analysis_runs r JOIN projects p ON p.id=r.projec"
                "t_id WHERE r.id=:id AND p.user_id=:owner"
            ),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("analysisNotFound", 404)
        creation = await self.one(
            "SELECT to_jsonb(e) FROM activity_events e WHERE analysis_run_id=:id "
            "AND event_type='analysis_created'",
            {"id": identifier},
        )
        value["purpose"] = (
            creation["payload"].get("purpose", "analysis") if creation else "analysis"
        )
        return value

    async def finish_run(self, owner, identifier, status, result, error=None):
        current = await self.run(owner, identifier)
        from scope_guard.domain.drafts.workflow import transition

        transition("analysis", current["status"], status)
        value = await self.one(
            (
                "UPDATE analysis_runs SET status=:status,started_at=CASE WHEN :status='ru"
                "nning' THEN now() ELSE started_at END,finished_at=CASE WHEN :status='run"
                "ning' THEN NULL ELSE now() END,result_snapshot=CAST(:result AS jsonb),re"
                "sult_schema_version=:version,request_language=:language,error_code=:erro"
                "r WHERE id=:id AND status=:previous RETURNING to_jsonb(analysis_runs)"
            ),
            {
                "status": status,
                "result": encoded(result) if result else None,
                "version": 1 if result else None,
                "language": result.get("requestLanguage") if result else None,
                "error": error,
                "id": identifier,
                "previous": current["status"],
            },
        )
        if value is None:
            raise WorkflowError("analysisConflict", 409)
        if status != "running":
            await self.event(
                current["projectId"],
                UUID(current["idempotencyKey"]),
                "analysis_" + status,
                owner,
                {"status": status},
                analysis_run_id=identifier,
            )
        return value

    async def histories(self, owner, project):
        await self.project(owner, project)
        return await self.many(
            (
                "SELECT to_jsonb(h) FROM history_entries h WHERE project_id=:project ORDE"
                "R BY date DESC,id DESC"
            ),
            {"project": project},
        )

    async def history(self, owner, identifier):
        value = await self.one(
            (
                "SELECT to_jsonb(h) FROM history_entries h JOIN projects p ON p.id=h.proj"
                "ect_id WHERE h.id=:id AND p.user_id=:owner"
            ),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("historyNotFound", 404)
        return value

    async def history_operation(self, owner, project, key, digest):
        await self.project(owner, project, lock=True)
        value = await self.one(
            (
                "SELECT to_jsonb(h) FROM history_entries h WHERE project_id=:project AND "
                "idempotency_key=:key"
            ),
            {"project": project, "key": key},
        )
        if value and value["requestHash"] != digest:
            raise WorkflowError("operationMismatch", 409)
        return value

    async def complete(self, owner, draft, context, run, key, digest):
        snapshot = {
            "version": 2,
            "requestText": draft["requestText"],
            "projectSnapshot": context,
            "analysis": run["resultSnapshot"],
            "draftDocument": draft["draftDocument"],
            "interfaceLocale": run["interfaceLocale"],
            "requestLanguage": run["requestLanguage"],
            "analysisCompletedAt": run["finishedAt"],
        }
        value = await self.one(
            (
                "INSERT INTO history_entries(project_id,date,request,verdict,summary,sour"
                "ce_draft_id,source_draft_revision,analysis_run_id,check_snapshot,schema_"
                "version,completed_at,saved_by_user_id,source_kind,idempotency_key,reques"
                "t_hash) VALUES(:project,CURRENT_DATE,:request,:verdict,:summary,:draft,:"
                "revision,:run,CAST(:snapshot AS jsonb),2,now(),:owner,'explicit',:key,:h"
                "ash) RETURNING to_jsonb(history_entries)"
            ),
            {
                "project": draft["projectId"],
                "request": draft["requestText"],
                "verdict": run["resultSnapshot"]["verdict"],
                "summary": run["resultSnapshot"]["summary"],
                "draft": draft["id"],
                "revision": int(draft["revision"]),
                "run": run["id"],
                "snapshot": encoded(snapshot),
                "owner": owner,
                "key": key,
                "hash": digest,
            },
        )
        await self.session.execute(
            text("UPDATE projects SET last_checked=CURRENT_DATE WHERE id=:id"),
            {"id": draft["projectId"]},
        )
        await self.event(
            draft["projectId"],
            key,
            "history_saved",
            owner,
            {"sourceRevision": draft["revision"]},
            draft_id=draft["id"],
            history_entry_id=value["id"],
        )
        return value

    async def agreement(self, owner, identifier):
        value = await self.one(
            (
                "SELECT to_jsonb(c) FROM change_orders c JOIN projects p ON p.id=c.projec"
                "t_id WHERE c.id=:id AND p.user_id=:owner"
            ),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("agreementNotFound", 404)
        return value

    async def agreements(self, owner, history):
        await self.history(owner, history)
        return await self.many(
            (
                "SELECT to_jsonb(c) FROM change_orders c WHERE history_entry_id=:history "
                "ORDER BY finalized_at DESC"
            ),
            {"history": history},
        )

    async def finalize(self, owner, history, key, digest):
        from scope_guard.domain.drafts.workflow import validate_agreement

        await self.project(owner, UUID(history["projectId"]), lock=True)
        prior = await self.one(
            (
                "SELECT to_jsonb(c) FROM change_orders c WHERE history_entry_id=:history "
                "AND idempotency_key=:key"
            ),
            {"history": history["id"], "key": key},
        )
        if prior:
            if prior["requestHash"] != digest:
                raise WorkflowError("operationMismatch", 409)
            return prior
        if await self.session.scalar(
            text(
                "SELECT 1 FROM change_orders WHERE history_entry_id=:history AND status='finalized'"
            ),
            {"history": history["id"]},
        ):
            raise WorkflowError("agreementAlreadyFinalized", 409)
        if history["sourceKind"] != "explicit":
            raise WorkflowError("legacyProvenanceMissing", 409)
        snapshot = history["checkSnapshot"]
        editor = validate_agreement(snapshot["draftDocument"].get("changeOrder"))
        identifier = uuid4()
        day = await self.session.scalar(text("SELECT to_char(now() AT TIME ZONE 'UTC','YYYYMMDD')"))
        reference = f"CO-{day}-{identifier.hex.upper()}"
        editor["reference"] = reference
        content = {
            "version": 1,
            "document": editor,
            "projectSnapshot": snapshot["projectSnapshot"],
            "analysisRunId": history["analysisRunId"],
            "clientAcceptanceVerified": False,
        }
        value = await self.one(
            (
                "INSERT INTO change_orders(id,project_id,history_entry_id,reference,conte"
                "nt_snapshot,schema_version,status,revision,finalized_by_user_id,idempote"
                "ncy_key,request_hash) VALUES(:id,:project,:history,:reference,CAST(:cont"
                "ent AS jsonb),1,'finalized',1,:owner,:key,:hash) RETURNING to_jsonb(chan"
                "ge_orders)"
            ),
            {
                "id": identifier,
                "project": history["projectId"],
                "history": history["id"],
                "reference": reference,
                "content": encoded(content),
                "owner": owner,
                "key": key,
                "hash": digest,
            },
        )
        await self.event(
            history["projectId"],
            key,
            "agreement_finalized",
            owner,
            {"reference": reference},
            history_entry_id=history["id"],
            change_order_id=identifier,
        )
        return value

    async def event_retry(self, owner, project, key, event, digest):
        await self.project(owner, UUID(str(project)), lock=True)
        row = await self.one(
            (
                "SELECT to_jsonb(e) FROM activity_events e WHERE project_id=:project AND "
                "operation_id=:key AND event_type=:event"
            ),
            {"project": project, "key": key, "event": event},
        )
        if row and row["payload"].get("requestHash") != digest:
            raise WorkflowError("operationMismatch", 409)
        return row

    async def void(self, owner, identifier, expected, key, digest):
        current = await self.agreement(owner, identifier)
        await self.project(owner, UUID(current["projectId"]), lock=True)
        if await self.event_retry(owner, current["projectId"], key, "agreement_voided", digest):
            return await self.agreement(owner, identifier)
        value = await self.one(
            (
                "UPDATE change_orders SET status='voided',revision=revision+1,voided_at=n"
                "ow(),updated_at=now() WHERE id=:id AND revision=:revision AND status='fi"
                "nalized' RETURNING to_jsonb(change_orders)"
            ),
            {"id": identifier, "revision": expected},
        )
        if not value:
            raise WorkflowError("agreementConflict", 409)
        await self.event(
            current["projectId"],
            key,
            "agreement_voided",
            owner,
            {"requestHash": digest, "revision": value["revision"]},
            change_order_id=identifier,
        )
        return value

    async def export(self, owner, identifier):
        value = await self.one(
            (
                "SELECT to_jsonb(e) FROM document_exports e JOIN projects p ON p.id=e.pro"
                "ject_id WHERE e.id=:id AND p.user_id=:owner"
            ),
            {"id": identifier, "owner": owner},
        )
        if not value:
            raise WorkflowError("exportNotFound", 404)
        return value

    async def exports(self, owner, agreement):
        await self.agreement(owner, agreement)
        return await self.many(
            (
                "SELECT to_jsonb(e) FROM document_exports e WHERE change_order_id=:id ORD"
                "ER BY created_at DESC"
            ),
            {"id": agreement},
        )

    async def create_export(self, owner, agreement, key, digest):
        await self.project(owner, UUID(agreement["projectId"]), lock=True)
        prior = await self.one(
            (
                "SELECT to_jsonb(e) FROM document_exports e WHERE change_order_id=:agreem"
                "ent AND idempotency_key=:key"
            ),
            {"agreement": agreement["id"], "key": key},
        )
        if prior:
            if prior["requestHash"] != digest:
                raise WorkflowError("operationMismatch", 409)
            return prior
        if (await self.agreement(owner, UUID(agreement["id"])))["status"] != "finalized":
            raise WorkflowError("agreementVoided", 409)
        value = await self.one(
            (
                "INSERT INTO document_exports(project_id,change_order_id,requested_by_use"
                "r_id,format,language,renderer_version,template_version,status,idempotenc"
                "y_key,request_hash) VALUES(:project,:agreement,:owner,'pdf',:language,'r"
                "eportlab-v1','change-order-v1','pending',:key,:hash) RETURNING to_jsonb("
                "document_exports)"
            ),
            {
                "project": agreement["projectId"],
                "agreement": agreement["id"],
                "owner": owner,
                "language": agreement["contentSnapshot"]["document"]["language"],
                "key": key,
                "hash": digest,
            },
        )
        await self.event(
            agreement["projectId"],
            key,
            "export_requested",
            owner,
            {},
            change_order_id=agreement["id"],
            document_export_id=value["id"],
        )
        return value

    async def retry_export(self, owner, identifier, key, digest):
        current = await self.export(owner, identifier)
        await self.project(owner, UUID(current["projectId"]), lock=True)
        if await self.event_retry(owner, current["projectId"], key, "export_retry", digest):
            return await self.export(owner, identifier)
        value = await self.one(
            (
                "UPDATE document_exports SET status='pending',error_code=NULL,lease_expir"
                "es_at=NULL,finished_at=NULL WHERE id=:id AND status='failed' RETURNING t"
                "o_jsonb(document_exports)"
            ),
            {"id": identifier},
        )
        if not value:
            raise WorkflowError("exportConflict", 409)
        await self.event(
            current["projectId"],
            key,
            "export_retry",
            owner,
            {"requestHash": digest},
            document_export_id=identifier,
        )
        return value

    async def evaluate(self, owner, run, feedback):
        result = run["resultSnapshot"]
        human = feedback.get("humanVerdict")
        accuracy = feedback["accuracy"]
        if accuracy == "correct":
            human = result["verdict"]
        elif accuracy == "debatable":
            human = None
        elif (
            accuracy != "wrong"
            or human not in ("in_scope", "borderline", "out_of_scope")
            or human == result["verdict"]
        ):
            raise WorkflowError("evaluationLabelInvalid")
        return await self.one(
            (
                "INSERT INTO evaluation_cases(user_id,analysis_run_id,scope,request,ai_ve"
                "rdict,human_verdict,ai_reasoning,accuracy,industry) VALUES(:owner,:run,:"
                "scope,:request,:ai,:human,:reason,:accuracy,:industry) ON CONFLICT(analy"
                "sis_run_id,user_id) WHERE analysis_run_id IS NOT NULL DO UPDATE SET accu"
                "racy=EXCLUDED.accuracy,human_verdict=EXCLUDED.human_verdict,updated_at=n"
                "ow() RETURNING to_jsonb(evaluation_cases)"
            ),
            {
                "owner": owner,
                "run": run["id"],
                "scope": run["projectSnapshot"]["scope"],
                "request": run["requestText"],
                "ai": result["verdict"],
                "human": human,
                "reason": result["reasoning"],
                "accuracy": accuracy,
                "industry": run["projectSnapshot"]["industry"],
            },
        )

    async def claim_export(self):
        row = await self.one(
            "SELECT to_jsonb(e) FROM document_exports e WHERE status='pending' ORDER "
            "BY created_at,id LIMIT 1 FOR UPDATE SKIP LOCKED"
        )
        if not row:
            return None
        claim = await self.one(
            (
                "UPDATE document_exports SET status='processing',attempt_count=attempt_co"
                "unt+1,lease_expires_at=now()+interval '120 seconds' WHERE id=:id AND sta"
                "tus='pending' RETURNING to_jsonb(document_exports)"
            ),
            {"id": row["id"]},
        )
        content = await self.session.scalar(
            text("SELECT content_snapshot FROM change_orders WHERE id=:id"),
            {"id": row["changeOrderId"]},
        )
        return {**claim, "contentSnapshot": content}

    async def heartbeat(self, identifier, attempt):
        value = await self.session.scalar(
            text(
                "UPDATE document_exports SET lease_expires_at=now()+interval '120 seconds"
                "' WHERE id=:id AND status='processing' AND attempt_count=:attempt AND le"
                "ase_expires_at>now() RETURNING id"
            ),
            {"id": identifier, "attempt": attempt},
        )
        return value is not None

    async def export_outcome(self, claim, metadata, error):
        values = metadata or {
            "objectKey": None,
            "checksum": None,
            "mimeType": None,
            "sizeBytes": None,
        }
        row = await self.one(
            (
                "UPDATE document_exports SET status=:status,object_key=:objectKey,checksu"
                "m=:checksum,mime_type=:mimeType,size_bytes=:sizeBytes,error_code=:error,"
                "finished_at=now(),lease_expires_at=NULL WHERE id=:id AND status='process"
                "ing' AND attempt_count=:attempt AND lease_expires_at>now() RETURNING to_"
                "jsonb(document_exports)"
            ),
            {
                **values,
                "status": "ready" if metadata else "failed",
                "error": error,
                "id": claim["id"],
                "attempt": claim["attemptCount"],
            },
        )
        if not row:
            return False
        operation = uuid5(NAMESPACE, claim["id"] + ":" + str(claim["attemptCount"]))
        await self.event(
            claim["projectId"],
            operation,
            "export_" + row["status"],
            payload={"attempt": claim["attemptCount"], "errorCode": error},
            document_export_id=claim["id"],
        )
        return True

    async def recover(self):
        abandoned = await self.many(
            (
                "UPDATE document_exports SET status='failed',error_code='lease_expired',l"
                "ease_expires_at=NULL,finished_at=now() WHERE status='processing' AND lea"
                "se_expires_at<=now() RETURNING to_jsonb(document_exports)"
            ),
            {},
        )
        for row in abandoned:
            await self.event(
                row["projectId"],
                uuid5(NAMESPACE, row["id"] + ":" + str(row["attemptCount"])),
                "export_failed",
                payload={"attempt": row["attemptCount"], "errorCode": "lease_expired"},
                document_export_id=row["id"],
            )
        await self.session.execute(
            text(
                "UPDATE document_exports SET status='pending',error_code=NULL,finished_at"
                "=NULL WHERE status='failed' AND attempt_count<3"
            )
        )
        interrupted = await self.many(
            (
                "UPDATE analysis_runs SET status='failed',error_code='interrupted',finish"
                "ed_at=now() WHERE status='running' AND started_at<now()-interval '660 se"
                "conds' RETURNING to_jsonb(analysis_runs)"
            ),
            {},
        )
        for row in interrupted:
            await self.event(
                row["projectId"],
                UUID(row["idempotencyKey"]),
                "analysis_failed",
                payload={"errorCode": "interrupted"},
                analysis_run_id=row["id"],
            )

    async def referenced_objects(self):
        values = (
            (
                await self.session.execute(
                    text("SELECT object_key FROM document_exports WHERE object_key IS NOT NULL")
                )
            )
            .scalars()
            .all()
        )
        return set(values)


class WorkflowUnitOfWork:
    def __init__(self, work):
        self.work = work
        self.workflow: WorkflowRepository

    async def __aenter__(self):
        await self.work.__aenter__()
        self.workflow = WorkflowSQLRepository(self.work.session)
        return self

    async def __aexit__(self, *args):
        await self.work.__aexit__(*args)

    async def commit(self):
        await self.work.commit()
