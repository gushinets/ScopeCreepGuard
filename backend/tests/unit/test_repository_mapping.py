from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from scope_guard.database.models import DraftRow, ProjectRow
from scope_guard.database.repositories.draft_persistence import stored
from scope_guard.database.repositories.projects import project
from scope_guard.domain.drafts.values import thaw_json
from scope_guard.domain.shared.enums import Currency, Industry, PricingModel


def test_project_mapping_detaches_precise_commercial_values():
    row = ProjectRow(
        id=uuid4(),
        name="Scope",
        scope="Five pages",
        client=None,
        industry=Industry.Development,
        start_date=date(2026, 1, 1),
        pricing_model=PricingModel.hourly,
        currency=Currency.EUR,
        hourly_rate=Decimal("125.10"),
        fixed_price=None,
        last_checked=None,
    )
    result = project(row)
    row.name = "Changed"
    row.hourly_rate = Decimal("999.00")
    assert result.card.name == "Scope"
    assert result.card.pricing.hourly_rate == Decimal("125.10")
    assert result.card.client.value is None
    with pytest.raises(FrozenInstanceError):
        result.card.name = "Mutable"


@pytest.mark.parametrize("snapshot", [None, {"name": "Historical", "client": None}])
def test_draft_mapping_keeps_legacy_null_and_detached_snapshot(snapshot):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = DraftRow(
        id=uuid4(),
        project_id=uuid4(),
        history_entry_id=uuid4(),
        project_snapshot=snapshot,
        analysis_snapshot={"verdict": "in_scope"},
        draft_document={"reply": {"text": "Saved"}},
        locale="en",
        request_language=None,
        client_material_language="en",
        created_at=now,
        updated_at=now,
    )
    result = stored(row, "Request")
    row.draft_document["reply"]["text"] = "Changed"
    assert thaw_json(result.document) == {"reply": {"text": "Saved"}}
    if snapshot is None:
        assert result.project_snapshot is None
    else:
        snapshot["name"] = "Current"
        assert thaw_json(result.project_snapshot) == {"name": "Historical", "client": None}
