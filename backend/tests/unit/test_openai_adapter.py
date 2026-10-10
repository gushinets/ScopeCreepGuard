import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scope_guard.modules.analysis.domain import AnalysisInput, GenerationContext, GenerationError

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


def test_one_adapter_operation_and_parameters():
    from scope_guard.infrastructure.llm.openai import OpenAIGeneration

    class Responses:
        calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                status="completed", output_text=json.dumps(FIXTURE["analysisFixture"])
            )

    responses = Responses()
    adapter = OpenAIGeneration("synthetic", client=SimpleNamespace(responses=responses))
    result = asyncio.run(adapter.analyze(INPUT))
    assert result.summary and len(responses.calls) == 1
    assert responses.calls[0]["model"] == "gpt-5.4-nano"
    assert responses.calls[0]["reasoning"] == {"effort": "medium"}
    assert responses.calls[0]["text"]["format"]["strict"] is True


@pytest.mark.parametrize(
    "status,text,code",
    [
        ("incomplete", "", "analysisFailed"),
        ("completed", " ", "analysisFailed"),
        ("completed", "{", "analysisInvalid"),
        ("completed", "{}", "analysisInvalid"),
    ],
)
def test_output_failures(status, text, code):
    from scope_guard.infrastructure.llm.openai import OpenAIGeneration

    class Responses:
        async def create(self, **kwargs):
            return SimpleNamespace(status=status, output_text=text)

    with pytest.raises(GenerationError, match=code):
        asyncio.run(
            OpenAIGeneration("synthetic", client=SimpleNamespace(responses=Responses())).analyze(
                INPUT
            )
        )


def test_retry_has_one_owner_and_honors_server_delays():
    import openai

    from scope_guard.infrastructure.llm.retry import invoke

    calls, delays = [], []

    async def attempt():
        calls.append(1)
        if len(calls) < 3:
            response = httpx.Response(
                429,
                headers={"retry-after-ms": "90000"},
                request=httpx.Request("POST", "https://example.invalid"),
            )
            raise openai.RateLimitError("sentinel private content", response=response, body=None)
        return "done"

    async def sleep(delay):
        delays.append(delay)

    assert asyncio.run(invoke(attempt, sleep=sleep)) == "done"
    assert len(calls) == 3 and delays == [90, 90]


@pytest.mark.parametrize("tone", ["warm", "neutral", "firm"])
def test_reply_uses_high_reasoning_and_selected_tone(tone):
    from scope_guard.infrastructure.llm.openai import OpenAIGeneration
    from scope_guard.modules.analysis.domain import ReplyInput

    calls = []

    class Responses:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                status="completed", output_text=json.dumps(FIXTURE["analysisFixture"])
            )

    value = ReplyInput(INPUT.context, INPUT.request, INPUT.locale, tone, "old 😀")
    result = asyncio.run(
        OpenAIGeneration(
            "synthetic", client=SimpleNamespace(responses=Responses())
        ).regenerate_reply(value)
    )
    assert result == FIXTURE["analysisFixture"]["replies"][tone]
    assert len(calls) == 1 and calls[0]["reasoning"] == {"effort": "high"}
    assert "old 😀" in calls[0]["input"]


def test_missing_key_and_provider_error_are_distinct_and_logs_are_private(caplog):
    from scope_guard.infrastructure.llm.openai import OpenAIGeneration

    with pytest.raises(GenerationError, match="analysisUnavailable"):
        asyncio.run(OpenAIGeneration(" \ufeff ").analyze(INPUT))

    class Responses:
        async def create(self, **kwargs):
            raise RuntimeError("sentinel private provider content cookie proof secret")

    with pytest.raises(GenerationError, match="analysisFailed"):
        asyncio.run(
            OpenAIGeneration("synthetic", client=SimpleNamespace(responses=Responses())).analyze(
                INPUT
            )
        )
    assert "sentinel" not in caplog.text
    for record in caplog.records:
        assert "sentinel" not in str(record.__dict__)


@pytest.mark.parametrize(
    "status,text",
    [
        ("incomplete", ""),
        ("completed", "{"),
        ("completed", "{}"),
        (
            "completed",
            json.dumps(
                {
                    "clientLanguage": "en",
                    "replies": {"warm": "a", "neutral": "b", "firm": "c"},
                    "changeOrder": None,
                }
            ),
        ),
    ],
)
def test_material_output_and_applicability_failures(status, text):
    from scope_guard.infrastructure.llm.openai import OpenAIGeneration
    from scope_guard.modules.analysis.domain import MaterialInput
    from scope_guard.modules.analysis.normalization import parse_analysis

    class Responses:
        async def create(self, **kwargs):
            return SimpleNamespace(status=status, output_text=text)

    value = MaterialInput(
        INPUT.context, INPUT.request, INPUT.locale, "en", parse_analysis(FIXTURE["analysisFixture"])
    )
    with pytest.raises(GenerationError, match="analysisInvalid"):
        asyncio.run(
            OpenAIGeneration(
                "synthetic", client=SimpleNamespace(responses=Responses())
            ).translate_materials(value)
        )


def test_retry_cancellation_does_not_replay():
    from scope_guard.infrastructure.llm.retry import invoke

    async def run():
        entered = asyncio.Event()
        attempts = []

        async def attempt():
            attempts.append(1)
            raise TimeoutError

        async def sleep(delay):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(invoke(attempt, sleep=sleep))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert attempts == [1]

    asyncio.run(run())


@pytest.mark.parametrize(
    "status,override,expected",
    [
        (408, None, True),
        (409, None, True),
        (429, None, True),
        (500, None, True),
        (400, None, False),
        (500, "false", False),
        (400, "true", True),
    ],
)
def test_retry_classification(status, override, expected):
    import openai

    from scope_guard.infrastructure.llm.retry import should_retry

    response = httpx.Response(
        status,
        headers={"x-should-retry": override} if override else {},
        request=httpx.Request("POST", "https://example.invalid"),
    )
    assert should_retry(openai.APIStatusError("private", response=response, body=None)) == expected


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"retry-after-ms": "90000"}, 90),
        ({"retry-after-ms": "100ms", "retry-after": "2"}, 0.1),
        ({"retry-after-ms": "0", "retry-after": "2"}, 2),
        ({"retry-after": "-1"}, 0),
        ({"retry-after": "bad"}, 0),
        ({}, 0.5),
    ],
)
def test_retry_delay_legacy_header_semantics(headers, expected):
    from scope_guard.infrastructure.llm.retry import retry_delay

    error = SimpleNamespace(response=SimpleNamespace(headers=headers))
    assert retry_delay(error, 0, random_value=lambda: 0) == expected


def test_attempt_timeout_uses_600_seconds_and_only_three_attempts(monkeypatch):
    from contextlib import asynccontextmanager

    from scope_guard.infrastructure.llm import retry

    deadlines, attempts = [], []

    @asynccontextmanager
    async def timeout(seconds):
        deadlines.append(seconds)
        yield
        raise TimeoutError

    monkeypatch.setattr(retry.asyncio, "timeout", timeout)

    async def attempt():
        attempts.append(1)

    async def sleep(seconds):
        pass

    with pytest.raises(TimeoutError):
        asyncio.run(retry.invoke(attempt, sleep=sleep))
    assert deadlines == [600, 600, 600] and attempts == [1, 1, 1]
