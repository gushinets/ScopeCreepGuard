import asyncio
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from uuid import UUID

import pytest

from scope_guard.api.project_input import parse_project
from scope_guard.api.project_output import project_to_wire
from scope_guard.core.contracts import Industry, Verdict
from scope_guard.infrastructure.database.models import ProjectRow
from scope_guard.infrastructure.database.repositories.projects import project
from scope_guard.modules.projects.domain import ProjectDetail, ProjectHistoryEntry
from scope_guard.modules.projects.use_cases import ProjectService


def test_parser_returns_nested_immutable_project_card():
    card = parse_project(
        {
            "name": "Site",
            "scope": "Five pages",
            "industry": "Development",
            "startDate": "2026-10-10",
            "pricingModel": "hourly",
            "currency": "EUR",
            "hourlyRate": "100.20",
            "clientName": "Owner",
        }
    )
    assert is_dataclass(card), "project parsing must return a typed value, not a mutable dict"
    for value, field, replacement in (
        (card, "name", "Changed"),
        (card.scope, "text", "Changed scope"),
        (card.pricing, "hourly_rate", None),
        (card.dates, "start", None),
        (card.dates.start, "value", "2000-01-01"),
        (card.client, "value", "Other"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field, replacement)


def test_repository_converts_row_to_detached_immutable_card():
    row = ProjectRow(
        id=UUID("10000000-0000-4000-8000-000000000001"),
        name="Legacy",
        scope="Agreed scope",
        industry=Industry.Design,
    )
    entity = project(row)
    assert is_dataclass(entity.card), "repository must not return a mutable card mapping"
    row.scope = "Changed database state"
    assert entity.card.scope.text == "Agreed scope"
    assert entity.card.pricing.model is None
    with pytest.raises(FrozenInstanceError):
        entity.card.scope.text = "Mutated"  # type: ignore[misc]


def test_use_case_returns_immutable_detail_instead_of_wire_mapping():
    key = UUID("10000000-0000-4000-8000-000000000001")
    entity = project(ProjectRow(id=key, name="Legacy", scope="Scope", industry=Industry.Design))

    class Work:
        projects = None
        history = None

        async def __aenter__(self):
            self.projects = self.history = self
            return self

        async def __aexit__(self, *args):
            pass

        async def get_owned(self, owner, identifier):
            return entity

        async def for_projects(self, identifiers):
            return ()

    detail = asyncio.run(ProjectService(Work).get(str(key), str(key)))
    assert is_dataclass(detail), "application output must be an immutable project detail"
    with pytest.raises(FrozenInstanceError):
        detail.project.card.name = "Changed"


def test_parser_does_not_retain_mutable_request_data():
    body = {
        "name": "Site",
        "scope": "Five pages",
        "industry": "Development",
        "startDate": "2026-10-10",
        "pricingModel": "fixed",
        "currency": "EUR",
        "fixedPrice": "50.00",
    }
    card = parse_project(body)
    body.update(name="Changed", scope="Changed", fixedPrice="999.00", clientName="Injected")
    assert card.name == "Site"
    assert card.scope.text == "Five pages"
    assert str(card.pricing.fixed_price) == "50.00"
    assert card.client.supplied is False and card.client.value is None


def test_serializer_allocates_fresh_nested_json_without_domain_aliases():
    key = UUID("10000000-0000-4000-8000-000000000001")
    entity = project(ProjectRow(id=key, name="Legacy", scope="Scope", industry=Industry.Design))
    entry = ProjectHistoryEntry(
        key, key, date(2026, 10, 10), "Request", Verdict.in_scope, "Summary"
    )
    detail = ProjectDetail(entity, (entry,))
    wire = project_to_wire(detail)
    wire["name"] = "Changed"
    wire["history"][0]["summary"] = "Changed"
    wire["history"].append({"injected": True})
    fresh = project_to_wire(detail)
    assert fresh["name"] == "Legacy"
    assert fresh["history"] == [
        {
            "id": str(key),
            "date": "2026-10-10",
            "request": "Request",
            "verdict": "in_scope",
            "summary": "Summary",
        }
    ]
    assert "lastChecked" not in fresh and fresh["startDate"] is None
    with pytest.raises(FrozenInstanceError):
        detail.history[0].summary = "Changed"  # type: ignore[misc]
