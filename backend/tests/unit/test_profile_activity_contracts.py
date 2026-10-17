from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from uuid import uuid4

import pytest

from scope_guard.domain.activity import ActivityEvent
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.profiles import validate_changes


def event(**values):
    return ActivityEvent(
        profile_id=uuid4(),
        operation_id=uuid4(),
        event_type="profile.updated",
        source="profile",
        deduplication_key="command:1",
        actor_user_id=uuid4(),
        **values,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"revision": "0"},
        {"revision": True},
        {"revision": -1},
        {"changedFields": ["full user request"]},
        {"password": "secret"},
    ],
)
def test_event_rejects_invalid_typed_or_private_payload(payload):
    with pytest.raises(ValueError, match="invalid_event_payload"):
        event(payload=payload)


def test_event_payload_is_detached_and_deeply_immutable():
    fields = ["profession"]
    value = event(payload={"revision": "2", "changedFields": fields})
    fields.append("private")
    assert value.payload["changedFields"] == ("profession",)
    with pytest.raises(TypeError):
        value.payload["revision"] = "3"
    with pytest.raises(FrozenInstanceError):
        value.event_type = "profile.created"
    with pytest.raises(ValueError, match="invalid_event_timestamp"):
        replace(value, occurred_at=datetime(2026, 10, 16))


@pytest.mark.parametrize(
    "changes",
    [
        {"userId": str(uuid4())},
        {"analyticsExcluded": True},
        {"status": None},
        {"preferences": {"timezone": "invented/zone"}},
        {"profession": "x" * 251},
    ],
)
def test_profile_contract_rejects_owner_exclusion_and_invalid_preferences(changes):
    with pytest.raises(WorkflowError, match="profileInvalid"):
        validate_changes(changes)
