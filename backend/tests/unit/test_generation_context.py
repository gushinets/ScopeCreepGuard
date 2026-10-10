import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from scope_guard.modules.analysis.context import historical_context
from scope_guard.modules.analysis.domain import (
    ABSENT,
    GenerationContext,
    GenerationError,
    HistoricalSelector,
    freeze,
)
from scope_guard.modules.drafts.generation_context import HistoricalGenerationDraft, from_draft

CURRENT = GenerationContext(
    "10000000-0000-4000-8000-000000000001",
    "Current",
    "Today",
    "Development",
    "Current scope",
    "2026-01-01",
    "hourly",
    "EUR",
    "100.00",
    None,
)
DRAFT = HistoricalGenerationDraft(CURRENT.project_id, "request", None, "Historical", "Saved client")


def test_null_historical_context_cannot_import_current_scope_or_prices():
    context = from_draft(CURRENT, DRAFT)
    assert context.scope == "" and context.start_date is None and context.hourly_rate is None
    assert context.name == "Historical" and context.client_name == "Saved client"


@pytest.mark.parametrize(
    "client,expected", [(ABSENT, "Saved client"), (None, None), ("", ""), ("Old", "Old")]
)
def test_legacy_missing_and_null_clients_differ(client, expected):
    snapshot = {"name": "Old", "scope": "Old scope"}
    if client != ABSENT:
        snapshot["clientName"] = client
    context = from_draft(CURRENT, replace(DRAFT, project_snapshot=freeze(snapshot)))
    assert context.client_name == expected and context.scope == "Old scope"


@pytest.mark.parametrize(
    "draft", [None, replace(DRAFT, project_id="other"), replace(DRAFT, request="other")]
)
def test_draft_precedence_and_binding(draft):
    class Repository:
        async def get_owned(self, *args):
            return draft

    class Proofs:
        def verify(self, *args):
            raise AssertionError("invalid supplied draft must not fall back to proof")

    with pytest.raises(GenerationError, match="draftProofInvalid"):
        asyncio.run(
            historical_context(
                SimpleNamespace(drafts=Repository()),
                Proofs(),
                CURRENT.project_id,
                CURRENT,
                "request",
                HistoricalSelector(CURRENT.project_id, "proof"),
                "en",
            )
        )
