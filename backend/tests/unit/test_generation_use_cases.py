import asyncio
import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

from scope_guard.core.contracts import Industry
from scope_guard.modules.analysis.domain import AnalyzeCommand, GenerationError, LocaleResolution
from scope_guard.modules.analysis.normalization import parse_analysis
from scope_guard.modules.projects.domain import (
    AgreedScope,
    OptionalClient,
    PricingConfiguration,
    Project,
    ProjectCard,
    ProjectDates,
)

OWNER = "11111111-1111-4111-8111-111111111111"
PROJECT = "22222222-2222-4222-8222-222222222222"
FIXTURE = json.loads(
    (Path(__file__).parents[3] / "contracts/compatibility/any-640/generation.json").read_text(
        encoding="utf-8"
    )
)


def workflow():
    from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
    from scope_guard.infrastructure.llm.rate_limit import GenerationLimiter
    from scope_guard.modules.analysis.use_cases import GenerationUseCases

    class Work:
        active = False
        projects = None
        history = None
        drafts = None
        project = Project(
            UUID(PROJECT),
            ProjectCard(
                "name",
                AgreedScope("scope"),
                Industry.Development,
                ProjectDates(None),
                PricingConfiguration(None, None, None, None),
                OptionalClient(None),
            ),
        )

        async def __aenter__(self):
            self.active = True
            self.projects = self
            return self

        async def __aexit__(self, *args):
            self.active = False

        async def get_owned(self, owner, project):
            assert owner == UUID(OWNER)
            return self.project if project == UUID(PROJECT) else None

    work = Work()

    class Generator:
        calls = 0

        async def analyze(self, value):
            assert not work.active, "read transaction leaked across provider call"
            self.calls += 1
            return parse_analysis(FIXTURE["analysisFixture"], value.locale)

    generator = Generator()
    return (
        GenerationUseCases(
            lambda: work,
            generator,
            DraftProofs("synthetic", lambda: 1000),
            GenerationLimiter(),
            lambda: 1000,
        ),
        work,
        generator,
    )


def test_analyze_closes_read_transaction_and_generates_once():
    service, work, generator = workflow()
    outcome = asyncio.run(
        service.analyze(OWNER, AnalyzeCommand(PROJECT, "request"), LocaleResolution("en"))
    )
    assert outcome.proof and generator.calls == 1 and not work.active


def test_precedence_size_consumes_allowance_but_scope_does_not():
    service, work, generator = workflow()
    work.project = replace(work.project, card=replace(work.project.card, scope=AgreedScope("")))
    for _ in range(12):
        with pytest.raises(GenerationError, match="scopeRequired"):
            asyncio.run(
                service.analyze(OWNER, AnalyzeCommand(PROJECT, "request"), LocaleResolution())
            )
    work.project = replace(
        work.project, card=replace(work.project.card, scope=AgreedScope("scope"))
    )
    for _ in range(10):
        with pytest.raises(GenerationError, match="analysisInputTooLarge"):
            asyncio.run(
                service.analyze(
                    OWNER, AnalyzeCommand(PROJECT, "x" * 100001), LocaleResolution(failed=True)
                )
            )
    with pytest.raises(GenerationError, match="analysisRateLimited"):
        asyncio.run(service.analyze(OWNER, AnalyzeCommand(PROJECT, "request"), LocaleResolution()))
    assert generator.calls == 0
