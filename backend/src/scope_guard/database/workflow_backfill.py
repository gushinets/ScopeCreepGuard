"""Resumable, lossless per-project import through the guarded migration runner."""

import json
from uuid import UUID, uuid4, uuid5

from sqlalchemy import text

from scope_guard.domain.drafts.workflow import empty_document, operation_hash, validate_document

NAMESPACE = UUID("54954954-9549-4549-8549-549549549549")
LEGACY_FIELDS = (
    "id",
    "project_id",
    "history_entry_id",
    "idempotency_key",
    "project_snapshot",
    "analysis_snapshot",
    "draft_document",
    "locale",
    "request_language",
    "client_material_language",
    "change_order_labels",
    "status",
    "created_at",
    "updated_at",
)


def legacy_document(raw: dict) -> dict:
    old = raw.get("draft_document") or {}
    result = empty_document(raw.get("client_material_language") or "en")
    reply = old.get("reply") or {}
    result["reply"].update({k: reply[k] for k in ("text", "tone", "generated") if k in reply})
    result["changeOrder"] = old.get("changeOrder")
    # Refuse an unsupported editor conversion rather than silently changing legacy terms.
    # The surrounding project transaction rolls back and can be resumed after review.
    return validate_document(result)


def raw_legacy(row: dict) -> dict:
    return {key: row.get(key) for key in LEGACY_FIELDS}


def backfill(engine) -> int:
    with engine.connect() as connection:
        identifiers = (
            connection.execute(text("SELECT id FROM projects ORDER BY id")).scalars().all()
        )
    count = 0
    for identifier in identifiers:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": identifier}
            )
            if connection.scalar(
                text("SELECT 1 FROM drafts WHERE project_id=:id AND revision IS NOT NULL"),
                {"id": identifier},
            ):
                continue
            rows = [
                dict(row[0])
                for row in connection.execute(
                    text(
                        "SELECT to_jsonb(d) FROM drafts d WHERE project_id=:id ORDER BY updated_a"
                        "t DESC,created_at DESC,id DESC FOR UPDATE"
                    ),
                    {"id": identifier},
                )
            ]
            selected = rows[0] if rows else None
            draft_id = UUID(selected["id"]) if selected else uuid5(NAMESPACE, str(identifier))
            ordered: list[dict | None] = []
            remaining: list[dict] = sorted(rows[1:], key=lambda row: row["id"])
            ordered.extend(remaining)
            if selected:
                ordered.append(selected)
            history_rows = (
                connection.execute(
                    text("SELECT to_jsonb(h) FROM history_entries h WHERE project_id=:id"),
                    {"id": identifier},
                )
                .scalars()
                .all()
            )
            for history in history_rows:
                original = {
                    key: history[key]
                    for key in ("id", "project_id", "date", "request", "verdict", "summary")
                }
                associated = next(
                    (raw_legacy(row) for row in rows if row["history_entry_id"] == history["id"]),
                    None,
                )
                snapshot = {
                    "version": 1,
                    "legacy": original,
                    "capturedDraft": associated,
                    "provenance": {
                        "completionVerified": False,
                        "historicalScopeKnown": bool(associated and associated["project_snapshot"]),
                        "editorCapturedAtMigration": associated is not None,
                    },
                    "projectSnapshot": None,
                    "analysis": None,
                    "document": None,
                }
                connection.execute(
                    text(
                        "UPDATE history_entries SET check_snapshot=CAST(:snapshot AS jsonb),schem"
                        "a_version=1,source_kind='legacy_unverified' WHERE id=:id AND check_snaps"
                        "hot IS NULL"
                    ),
                    {"snapshot": json.dumps(snapshot), "id": history["id"]},
                )
            if not selected:
                connection.execute(
                    text(
                        "INSERT INTO drafts(id,project_id,draft_document,request_text,analysis_is"
                        "_stale,revision) VALUES(:id,:project,CAST(:document AS jsonb),'',true,1)"
                    ),
                    {
                        "id": draft_id,
                        "project": identifier,
                        "document": json.dumps(empty_document()),
                    },
                )
                ordered = [None]
            for number, row in enumerate(ordered, 1):
                raw = raw_legacy(row) if row else None
                request = next(
                    (
                        h["request"]
                        for h in history_rows
                        if row and h["id"] == row["history_entry_id"]
                    ),
                    "",
                )
                document = legacy_document(raw) if raw else empty_document()
                snapshot = {
                    "version": 2,
                    "id": str(draft_id),
                    "projectId": str(identifier),
                    "revision": str(number),
                    "requestText": request,
                    "lastAnalysisRunId": None,
                    "analysisIsStale": True,
                    "draftDocument": document,
                    "context": raw["project_snapshot"] if raw else None,
                    "legacy": raw,
                    "legacyDigest": operation_hash(raw) if raw else None,
                    "importOrderingOnly": bool(raw),
                }
                connection.execute(
                    text(
                        "INSERT INTO draft_revisions(id,draft_id,project_id,revision,state_snapsh"
                        "ot,schema_version,reason,actor_type,operation_id,request_hash) VALUES(:i"
                        "d,:draft,:project,:revision,CAST(:snapshot AS jsonb),2,:reason,'legacy',"
                        ":operation,:hash)"
                    ),
                    {
                        "id": UUID(row["id"]) if row else uuid4(),
                        "draft": draft_id,
                        "project": identifier,
                        "revision": number,
                        "snapshot": json.dumps(snapshot),
                        "reason": "legacy_import" if raw else "initial",
                        "operation": uuid5(
                            NAMESPACE, (row["id"] if row else str(identifier)) + ":import"
                        ),
                        "hash": operation_hash(snapshot),
                    },
                )
            final = snapshot
            connection.execute(
                text(
                    "UPDATE drafts SET request_text=:request,last_analysis_run_id=NULL,analys"
                    "is_is_stale=true,revision=:revision,draft_document=CAST(:document AS jso"
                    "nb) WHERE id=:id"
                ),
                {
                    "request": final["requestText"],
                    "revision": len(ordered),
                    "document": json.dumps(final["draftDocument"]),
                    "id": draft_id,
                },
            )
            connection.execute(
                text("UPDATE projects SET updated_at=now() WHERE id=:id AND updated_at IS NULL"),
                {"id": identifier},
            )
            count += 1
    return count


def verified_legacy_transfers(connection) -> list[UUID]:
    "Return only individually verified non-working rows; never infer transfer by count."
    rows = (
        connection.execute(
            text("SELECT to_jsonb(d) FROM drafts d WHERE revision IS NULL ORDER BY id FOR UPDATE")
        )
        .scalars()
        .all()
    )
    identifiers = []
    for row in rows:
        raw = raw_legacy(row)
        snapshot = connection.scalar(
            text(
                "SELECT state_snapshot FROM draft_revisions WHERE id=:id AND reason='lega"
                "cy_import' AND project_id=:project"
            ),
            {"id": row["id"], "project": row["project_id"]},
        )
        if (
            not snapshot
            or snapshot.get("legacy") != raw
            or snapshot.get("legacyDigest") != operation_hash(raw)
        ):
            raise RuntimeError("legacy_transfer_not_lossless:" + row["id"])
        identifiers.append(UUID(row["id"]))
    return identifiers


def verify_backfill(connection) -> None:
    missing = connection.scalar(
        text(
            "SELECT count(*) FROM projects p WHERE updated_at IS NULL OR NOT EXISTS(S"
            "ELECT 1 FROM drafts d WHERE d.project_id=p.id AND d.revision IS NOT NULL"
            ")"
        )
    )
    invalid = connection.scalar(
        text(
            "SELECT count(*) FROM drafts d WHERE revision IS NOT NULL AND NOT EXISTS("
            "SELECT 1 FROM draft_revisions r WHERE r.draft_id=d.id AND r.revision=d.r"
            "evision AND r.project_id=d.project_id)"
        )
    )
    histories = connection.scalar(
        text(
            "SELECT count(*) FROM history_entries WHERE check_snapshot IS NULL OR sou"
            "rce_kind IS NULL OR schema_version IS NULL"
        )
    )
    if missing or invalid or histories:
        raise RuntimeError("workflow_backfill_incomplete")
    for snapshot in connection.execute(
        text("SELECT state_snapshot FROM draft_revisions WHERE reason='legacy_import'")
    ).scalars():
        raw = snapshot.get("legacy")
        if (
            not raw
            or set(raw) != set(LEGACY_FIELDS)
            or operation_hash(raw) != snapshot.get("legacyDigest")
        ):
            raise RuntimeError("legacy_envelope_integrity_failed")
    verified_legacy_transfers(connection)


def retire_verified_legacy_rows(connection) -> None:
    "Move-only contraction: exact IDs, byte-equivalent JSON evidence, count assertion."
    verify_backfill(connection)
    for identifier in verified_legacy_transfers(connection):
        result = connection.execute(
            text("DELETE FROM drafts WHERE id=:id AND revision IS NULL"), {"id": identifier}
        )
        if result.rowcount != 1:
            raise RuntimeError("legacy_transfer_changed")
