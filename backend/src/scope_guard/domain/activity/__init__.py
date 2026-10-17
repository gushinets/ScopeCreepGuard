"""Immutable, content-free confirmed activity contracts."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Literal
from uuid import UUID

from scope_guard.domain.drafts.workflow import WorkflowError

ALIASES = {
    "initial": "project.created",
    "project_change": "project.updated",
    "restore": "draft.restored",
    "analysis_created": "check.requested",
    "analysis_failed": "check.failed",
    "agreement_finalized": "change_order.finalized",
    "agreement_voided": "change_order.voided",
}
FIELDS = {
    "profile.created": {"revision"},
    "profile.updated": {"revision", "changedFields"},
    "project.created": {"revision", "changedFields"},
    "project.updated": {"revision", "changedFields", "archived"},
    "draft.updated": {"revision", "changedFields", "reason"},
    "draft.restored": {"revision", "changedFields"},
    "evaluation.changed": {"accuracy", "humanVerdict", "evaluationId", "updatedAt"},
    "change_order.finalized": {"reference"},
    "change_order.voided": {"requestHash", "revision"},
    "history_saved": {"sourceRevision", "requestHash"},
}
for _kind in ("check", "translation", "estimate", "reply"):
    for _phase in ("requested", "completed", "failed", "cancelled", "regenerated"):
        FIELDS[f"{_kind}.{_phase}"] = {
            "sourceRevision",
            "purpose",
            "status",
            "errorCode",
            "applied",
            "kind",
            "requestHash",
        }
for _name in ("requested", "retry", "ready", "failed", "expired"):
    FIELDS["export_" + _name] = {"attempt", "errorCode", "requestHash"}
FIELDS["analysis_succeeded"] = {"status"}  # historical adapter only


class EventConflict(WorkflowError):
    def __init__(self):
        super().__init__("operationMismatch", 409)


@dataclass(frozen=True)
class ActivityEvent:
    profile_id: UUID | str
    operation_id: UUID | str
    event_type: str
    source: str
    deduplication_key: str
    actor_type: Literal["user", "system"] = "user"
    actor_user_id: UUID | str | None = None
    project_id: UUID | str | None = None
    product_session_id: UUID | str | None = None
    occurred_at: datetime | None = None
    payload: Mapping = field(default_factory=dict)
    links: Mapping = field(default_factory=dict)
    legacy_event_type: str | None = None
    payload_json: str = field(init=False, repr=False)

    def __post_init__(self):
        if self.links.keys() - {
            "draft_id",
            "draft_revision_id",
            "analysis_run_id",
            "history_entry_id",
            "change_order_id",
            "document_export_id",
        }:
            raise ValueError("invalid_event_links")
        allowed = FIELDS.get(self.event_type)
        if allowed is None or self.payload.keys() - allowed:
            raise ValueError("invalid_event_payload")
        if self.actor_type not in ("user", "system") or (
            self.actor_type == "user" and not self.actor_user_id
        ):
            raise ValueError("invalid_event_actor")
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,100}", self.source):
            raise ValueError("invalid_event_source")
        if not self.deduplication_key.strip() or len(self.deduplication_key) > 250:
            raise ValueError("invalid_event_identity")
        if self.occurred_at is not None and self.occurred_at.utcoffset() is None:
            raise ValueError("invalid_event_timestamp")
        payload = dict(self.payload)
        for key, value in payload.items():
            if key in ("revision", "sourceRevision", "attempt") and (
                isinstance(value, bool)
                or not isinstance(value, (str, int))
                or not re.fullmatch(r"[1-9][0-9]*", str(value))
                or int(value) >= 2**63
            ):
                raise ValueError("invalid_event_payload")
            if key in ("applied", "archived") and not isinstance(value, bool):
                raise ValueError("invalid_event_payload")
            if key == "changedFields":
                if not isinstance(value, (list, tuple)) or any(
                    not isinstance(v, str) or not re.fullmatch(r"[A-Za-z.]{1,64}", v) for v in value
                ):
                    raise ValueError("invalid_event_payload")
                payload[key] = list(value)
            elif value is not None and not isinstance(value, (str, bool, int)):
                raise ValueError("invalid_event_payload")
            elif isinstance(value, str) and (
                len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9_.:+-]*", value)
            ):
                raise ValueError("invalid_event_payload")
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        if len(encoded) > 4096:
            raise ValueError("invalid_event_payload")
        object.__setattr__(self, "payload_json", encoded)
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(
                {k: tuple(v) if isinstance(v, list) else v for k, v in payload.items()}
            ),
        )
        object.__setattr__(self, "links", MappingProxyType(dict(self.links)))


def canonical_type(name, payload=None):
    if name in {
        "autosave",
        "manual_save",
        "tone_change",
        "language_change",
        "change_order_edit",
        "clear",
        "analysis_apply",
        "regenerate",
    }:
        return "draft.updated"
    result = ALIASES.get(name, name)
    if result.startswith("check.") and (payload or {}).get("purpose") == "estimate":
        result = result.replace("check.", "estimate.")
    return result
