"""One immutable journal with content-aware receipts, including legacy identities."""

import json
from datetime import UTC, datetime

from sqlalchemy import text

from scope_guard.database.repositories.sessions import ProductSessions
from scope_guard.domain.activity import ActivityEvent, EventConflict
from scope_guard.domain.drafts.workflow import WorkflowError

LINK_TABLES = {
    "draft_id": "drafts",
    "draft_revision_id": "draft_revisions",
    "analysis_run_id": "analysis_runs",
    "history_entry_id": "history_entries",
    "change_order_id": "change_orders",
    "document_export_id": "document_exports",
}


async def profiles_supported(session):
    if "profiles_supported" not in session.info:
        session.info["profiles_supported"] = bool(
            await session.scalar(text("SELECT to_regclass('public.profiles') IS NOT NULL"))
        )
    return session.info["profiles_supported"]


class EventRepository:
    def __init__(self, session):
        self.session = session

    async def append(self, event: ActivityEvent, *, touch_session=False):
        # All supported writers lock profile before project and journal identities.
        await self.session.execute(
            text("SELECT id FROM profiles WHERE id=:id FOR UPDATE"), {"id": event.profile_id}
        )
        for identity in sorted(
            {
                f"event:{event.source}:{event.deduplication_key}",
                f"legacy:{event.project_id or event.profile_id}:{event.operation_id}",
            }
        ):
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": identity}
            )
        prior = (
            (
                await self.session.execute(
                    text(
                        "SELECT * FROM activity_events WHERE (source=:source AND "
                        "deduplication_key=:key) "
                        "OR (event_version IS NULL AND project_id=:project AND "
                        "operation_id=:operation "
                        "AND event_type=:legacy)"
                    ),
                    {
                        "source": event.source,
                        "key": event.deduplication_key,
                        "project": event.project_id,
                        "operation": event.operation_id,
                        "legacy": event.legacy_event_type or event.event_type,
                    },
                )
            )
            .mappings()
            .all()
        )
        values = {
            "profile_id": event.profile_id,
            "project_id": event.project_id,
            "operation_id": event.operation_id,
            "event_type": event.event_type,
            "actor_type": event.actor_type,
            "actor_user_id": event.actor_user_id,
            **{key: event.links.get(key) for key in LINK_TABLES},
        }
        if prior:
            if len(prior) != 1:
                raise EventConflict()
            row = prior[0]
            compared = dict(values)
            if row["event_version"] is None:
                compared.pop("profile_id")
                compared["event_type"] = event.legacy_event_type or event.event_type
            if any(str(row[k]) != str(v) for k, v in compared.items()):
                raise EventConflict()
            if row["payload"] != json.loads(event.payload_json):
                raise EventConflict()
            if (
                event.occurred_at is not None
                and row["event_version"] is not None
                and (event.occurred_at != row["occurred_at"])
            ):
                raise EventConflict()
            if (
                event.product_session_id is not None
                and row["event_version"] is not None
                and (str(event.product_session_id) != str(row["product_session_id"]))
            ):
                raise EventConflict()
            return row["id"]
        await self.validate_links(event)
        session_id = event.product_session_id
        if session_id is None:
            session_id = self.session.info.get("activity_origin_session")
        if session_id is None and event.actor_type == "user":
            session_id = await ProductSessions(self.session).resolve(
                event.profile_id, touch=touch_session
            )
        now = datetime.now(UTC)
        occurred = event.occurred_at or now
        if occurred > now:
            raise ValueError("invalid_event_timestamp")
        columns = list(values) + [
            "product_session_id",
            "source",
            "deduplication_key",
            "occurred_at",
            "recorded_at",
        ]
        parameters = {
            **values,
            "product_session_id": session_id,
            "source": event.source,
            "deduplication_key": event.deduplication_key,
            "occurred_at": occurred,
            "recorded_at": now,
            "payload": event.payload_json,
        }
        identifier = await self.session.scalar(
            text(
                "INSERT INTO activity_events(" + ",".join(columns) + ",payload,payload_version,"
                "event_version) VALUES("
                + ",".join(":" + k for k in columns)
                + ",CAST(:payload AS jsonb),1,2) RETURNING id"
            ),
            parameters,
        )
        self.session.info["marketing_metrics_dirty"] = True
        return identifier

    async def validate_links(self, event):
        owner = await self.session.scalar(
            text("SELECT user_id FROM profiles WHERE id=:id"), {"id": event.profile_id}
        )
        if owner is None or (event.actor_user_id and str(owner) != str(event.actor_user_id)):
            raise WorkflowError("eventOwnerMismatch", 409)
        if event.links.keys() - LINK_TABLES.keys() or (event.links and not event.project_id):
            raise ValueError("invalid_event_links")
        if event.project_id:
            project = (
                (
                    await self.session.execute(
                        text("SELECT user_id,profile_id FROM projects WHERE id=:id FOR UPDATE"),
                        {"id": event.project_id},
                    )
                )
                .mappings()
                .first()
            )
            if (
                not project
                or project["user_id"] != owner
                or (project["profile_id"] and str(project["profile_id"]) != str(event.profile_id))
            ):
                raise WorkflowError("eventOwnerMismatch", 409)
            if project["profile_id"] is None:
                await self.session.execute(
                    text("UPDATE projects SET profile_id=:profile WHERE id=:id"),
                    {"profile": event.profile_id, "id": event.project_id},
                )
        linked = {}
        for key, value in event.links.items():
            row = (
                (
                    await self.session.execute(
                        text(
                            f"SELECT * FROM {LINK_TABLES[key]} WHERE id=:id AND project_id=:project"
                        ),
                        {"id": value, "project": event.project_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise WorkflowError("eventLinkMismatch", 409)
            linked[key] = row
        for child, parent, column in (
            ("draft_revision_id", "draft_id", "draft_id"),
            ("analysis_run_id", "draft_id", "source_draft_id"),
            ("history_entry_id", "draft_id", "source_draft_id"),
            ("history_entry_id", "analysis_run_id", "analysis_run_id"),
            ("change_order_id", "history_entry_id", "history_entry_id"),
            ("document_export_id", "change_order_id", "change_order_id"),
        ):
            if (
                child in linked
                and parent in event.links
                and (str(linked[child][column]) != str(event.links[parent]))
            ):
                raise WorkflowError("eventLinkMismatch", 409)
        if event.product_session_id and not await self.session.scalar(
            text("SELECT id FROM product_sessions WHERE id=:id AND profile_id=:profile"),
            {"id": event.product_session_id, "profile": event.profile_id},
        ):
            raise WorkflowError("eventLinkMismatch", 409)

    async def legacy_append(self, project, operation, name, owner, payload, links):
        """Explicit pre-0006 adapter; never used on the supported profile schema."""
        if links.keys() - LINK_TABLES.keys():
            raise ValueError("invalid_event_links")
        await self.session.execute(
            text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": project}
        )
        values = {
            "project_id": project,
            "operation_id": operation,
            "event_type": name,
            "actor_type": "user" if owner else "system",
            "actor_user_id": owner,
            **links,
        }
        prior = (
            (
                await self.session.execute(
                    text(
                        "SELECT * FROM activity_events WHERE project_id=:project AND "
                        "operation_id=:op "
                        "AND event_type=:name"
                    ),
                    {"project": project, "op": operation, "name": name},
                )
            )
            .mappings()
            .first()
        )
        if prior:
            if (
                any(str(prior[k]) != str(v) for k, v in values.items())
                or prior["payload"] != payload
            ):
                raise EventConflict()
            return prior["id"]
        return await self.session.scalar(
            text(
                "INSERT INTO activity_events("
                + ",".join(values)
                + ",payload,payload_version) VALUES("
                + ",".join(":" + k for k in values)
                + ",CAST(:payload AS jsonb),1) RETURNING id"
            ),
            {**values, "payload": json.dumps(payload)},
        )


async def llm_event(session, operation, phase, envelope=None):
    """One outcome per logical operation, independent of physical provider attempts."""
    if operation["kind"] in ("diagnostic", "agreement") or not await profiles_supported(session):
        return
    from scope_guard.database.repositories.workflow import WorkflowSQLRepository

    kind = {
        "check": "check",
        "estimate": "estimate",
        "translate": "translation",
        "regenerate": "reply",
    }[operation["kind"]]
    name = f"{kind}.{'regenerated' if phase == 'completed' and kind == 'reply' else phase}"
    links = {"draft_id": operation["draft_id"]}
    if operation.get("analysis_run_id"):
        links["analysis_run_id"] = operation["analysis_run_id"]
    if envelope and envelope.get("historyEntryId"):
        links["history_entry_id"] = envelope["historyEntryId"]
    if phase == "completed" and kind == "check" and not links.get("history_entry_id"):
        raise WorkflowError("savedCheckRequired", 409)
    payload = {"kind": operation["kind"], "status": "succeeded" if phase == "completed" else phase}
    if phase == "failed":
        error = operation.get("error") or {}
        payload["errorCode"] = error.get("code", "errors.analysisInvalid")
    if envelope and "applied" in envelope:
        payload["applied"] = envelope["applied"]
    if phase != "requested":
        session.info["activity_executor"] = "system"
        session.info["activity_origin_session"] = await session.scalar(
            text(
                "SELECT product_session_id FROM activity_events WHERE project_id=:project "
                "AND operation_id=:command AND event_type LIKE '%.requested' ORDER BY created_at "
                "LIMIT 1"
            ),
            {"project": operation["project_id"], "command": operation["command_key"]},
        )
    await WorkflowSQLRepository(session).event(
        operation["project_id"],
        operation["command_key"],
        name,
        operation["owner_id"],
        payload,
        **links,
    )
