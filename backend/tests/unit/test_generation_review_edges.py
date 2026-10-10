import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from scope_guard.core.contracts import Industry
from scope_guard.infrastructure.llm.language import normalize_language, supported_language
from scope_guard.infrastructure.llm.openai import OpenAIGeneration
from scope_guard.modules.analysis.domain import AnalysisInput, GenerationContext, GenerationError
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
INPUT = AnalysisInput(
    GenerationContext("id", "name", None, "Development", "scope", None, None, None, None, None),
    "request",
    "en",
)


def materials_workflow():
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

        async def translate_materials(self, value):
            self.calls += 1
            raise AssertionError("invalid submitted analysis reached provider")

    generator = Generator()
    service = GenerationUseCases(
        lambda: work,
        generator,
        DraftProofs("synthetic", lambda: 1000),
        GenerationLimiter(),
        lambda: 1000,
    )
    return service, work, generator


@pytest.mark.parametrize(
    "tag", ["no-bok", "abcd", "en-abc-abc", "en-a-foo-a-bar", "en-t-en-us-h0", "en-t-en-abc-abc"]
)
def test_intl_invalid_tags(tag):
    assert normalize_language(tag) is None
    assert supported_language(tag) is None


def test_intl_duplicate_unicode_key_keeps_first():
    assert normalize_language("en-u-ca-gregory-ca-buddhist") == "en-u-ca-gregory"


@pytest.mark.parametrize(
    "raw,canonical",
    [
        ("en-u-ca-yes", "en-u-ca"),
        ("en-u-ms-imperial", "en-u-ms-uksystem"),
        ("en-u-tz-usnavajo", "en-u-tz-usden"),
        ("uk-SU-u-ca-gregory", "uk-UA-u-ca-gregory"),
        ("en-t-en-us-h0-hybrid", "en-t-en-us-h0-hybrid"),
    ],
)
def test_intl_extensions_and_region_alias(raw, canonical):
    assert normalize_language(raw) == canonical


@pytest.mark.parametrize("field", ["confidence", "estimatedHours"])
def test_huge_model_number_is_invalid(field):
    raw = copy.deepcopy(FIXTURE["analysisFixture"])
    target = raw if field == "confidence" else raw["changeOrder"]
    target[field] = 10**400
    with pytest.raises(ValueError):
        parse_analysis(raw)
    adapter = OpenAIGeneration("synthetic")
    with pytest.raises(GenerationError, match="analysisInvalid"):
        adapter._analysis(SimpleNamespace(status="completed", output_text=json.dumps(raw)), INPUT)


@pytest.mark.parametrize("field", ["confidence", "estimatedHours"])
def test_huge_submitted_material_number_is_body_error_before_provider(field):
    from scope_guard.api.generation_input import parse_materials
    from scope_guard.modules.analysis.domain import LocaleResolution

    raw = copy.deepcopy(FIXTURE["analysisFixture"])
    (raw if field == "confidence" else raw["changeOrder"])[field] = 10**400
    service, work, generator = materials_workflow()
    command = parse_materials(
        {"projectId": PROJECT, "request": "request", "clientLanguage": "en", "analysis": raw}
    )
    with pytest.raises(GenerationError, match="requestBodyInvalid") as error:
        asyncio.run(service.translate_materials(OWNER, command, LocaleResolution("en")))
    assert error.value.status == 400 and generator.calls == 0 and not work.active


def test_limiter_concurrent_admission_is_atomic():
    from concurrent.futures import ThreadPoolExecutor

    from scope_guard.infrastructure.llm.rate_limit import GenerationLimiter

    limiter = GenerationLimiter()
    with ThreadPoolExecutor(max_workers=20) as workers:
        admitted = list(workers.map(lambda _: limiter.allow("user", 1000), range(100)))
    assert sum(admitted) == 10


def test_lone_surrogate_http_response():
    from scope_guard.api.routes.generation import GenerationJSONResponse

    response = GenerationJSONResponse({"reply": "\ud800"})
    assert json.loads(response.body) == {"reply": "\ud800"}
    assert b"\\ud800" in response.body


def test_lone_surrogate_reaches_official_sdk_transport():
    from scope_guard.infrastructure.llm.openai import GenerationOpenAI

    calls = []

    def transport(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"id": "resp_test", "status": "completed", "output": [], "object": "response"},
        )

    async def run():
        client = GenerationOpenAI(
            api_key="synthetic",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
        )
        try:
            await OpenAIGeneration("synthetic", client=client)._request(
                "analyze",
                {"instructions": "scope\ud800", "input": "request\udfff"},
                {},
                "scope_analysis",
                "medium",
            )
        finally:
            await client.close()

    asyncio.run(run())
    assert len(calls) == 1
    assert calls[0]["instructions"] == "scope\ud800"
    assert calls[0]["input"] == "request\udfff"
