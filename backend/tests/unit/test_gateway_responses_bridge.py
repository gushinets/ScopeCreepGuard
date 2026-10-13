"""Real pinned SDK bridge, provider HTTP double; no external model calls."""

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, ModelRetry, NativeOutput

from scope_guard.domain.llm.runtime import GatewayFailure, ProviderRequest
from scope_guard.integrations.llm.gateway import Binding, ProviderGateway
from scope_guard.integrations.llm.litellm_adapter import LiteLLMResponsesAdapter
from scope_guard.integrations.llm.pydanticai_model import GatewayResponsesModel


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str


class Ledger:
    def __init__(self):
        self.calls = []
        self.candidates = []

    async def reserve(self, request, transport_attempt):
        call = {
            "id": uuid4(),
            "semantic": request.semantic_attempt,
            "transport": transport_attempt,
            "request": request,
        }
        self.calls.append(call)
        return call["id"]

    async def complete(self, identifier, response=None, error=None):
        call = next(c for c in self.calls if c["id"] == identifier)
        call.update(response=response, error=error)

    async def checkpoint(self, request, response):
        self.candidates.append(response.text)

    async def feedback(self, binding, error):
        self.calls[-1]["validation"] = error


def test_timeout_has_one_retry_owner_and_consumes_uncertain_attempts():
    async def exercise():
        ledger = Ledger()

        class TimeoutAdapter:
            async def request(self, *_):
                raise TimeoutError

        gateway = ProviderGateway(ledger, TimeoutAdapter(), sleep=lambda _: asyncio.sleep(0))
        with pytest.raises(GatewayFailure, match="providerOutcomeUnknown"):
            await gateway.request(
                ProviderRequest(
                    Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium"),
                    1,
                    [{"role": "user", "content": "test"}],
                    {},
                    "test",
                    60,
                )
            )
        assert len(ledger.calls) == 2
        assert all(c["error"]["uncertain"] for c in ledger.calls)

    asyncio.run(exercise())


def response(text, index, usage=True):
    body = {
        "id": f"resp_{index}",
        "object": "response",
        "created_at": 1,
        "model": "gpt-5.4-nano",
        "status": "completed",
        "output": [
            {
                "id": f"msg_{index}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": json.dumps({"reply": text}), "annotations": []}
                ],
            }
        ],
    }
    if usage:
        body["usage"] = {
            "input_tokens": 37,
            "output_tokens": 12,
            "total_tokens": 49,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 3},
        }
    return body


@pytest.mark.parametrize("effort", ["medium", "high"])
def test_native_schema_feedback_reasoning_and_transport_attempts(effort):
    async def exercise():
        bodies = []

        def http(request):
            bodies.append(json.loads(request.content))
            if len(bodies) == 2:
                return httpx.Response(
                    429,
                    json={
                        "error": {
                            "message": "retry",
                            "type": "rate_limit_error",
                            "code": "rate_limit_exceeded",
                        }
                    },
                    headers={"retry-after": "0"},
                )
            text = "Русский ответ" if len(bodies) == 1 else "Respuesta en español."
            return httpx.Response(200, json=response(text, len(bodies)))

        ledger = Ledger()
        adapter = LiteLLMResponsesAdapter("synthetic", transport=httpx.MockTransport(http))
        gateway = ProviderGateway(ledger, adapter, sleep=lambda _: asyncio.sleep(0))
        binding = Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", effort)
        agent = Agent(
            model=GatewayResponsesModel(gateway, binding),
            output_type=NativeOutput(Output, strict=True),
            retries={"output": 2},
        )

        @agent.output_validator
        def validate(data):
            if data.reply != "Respuesta en español.":
                raise ModelRetry("reply.language: expected es; detected ru; preserve scope")
            return data

        try:
            result = await agent.run("¿Podéis añadir Arrow? Scope excludes Arrow.")
            assert result.output.reply == "Respuesta en español."
        finally:
            await adapter.close()
        assert len(bodies) == len(ledger.calls) == 3
        assert [(c["semantic"], c["transport"]) for c in ledger.calls] == [(1, 1), (2, 1), (2, 2)]
        for body in bodies:
            fmt = body["text"]["format"]
            assert fmt["type"] == "json_schema" and fmt["strict"] is True
            assert fmt["schema"]["additionalProperties"] is False
            assert fmt["schema"]["required"] == ["reply"]
            assert body["reasoning"] == {"effort": effort}
            assert body["max_output_tokens"] == 4096
        assert "reply.language" in json.dumps(bodies[1]["input"], ensure_ascii=False)
        preceding = next(
            item["content"] for item in bodies[1]["input"] if item["role"] == "assistant"
        )
        assert json.loads(preceding)["reply"] == "Русский ответ"
        assert ledger.calls[0]["response"].input_tokens == 37
        assert ledger.calls[0]["response"].reported_cost is None
        assert ledger.calls[2]["response"].response_id
        assert len(ledger.candidates) == 2

    asyncio.run(exercise())


def test_schema_error_is_not_retried_or_downgraded():
    async def exercise():
        requests = []

        def http(request):
            requests.append(json.loads(request.content))
            return httpx.Response(
                422,
                json={
                    "error": {
                        "message": "schema rejected",
                        "type": "invalid_request_error",
                        "code": "invalid_json_schema",
                    }
                },
            )

        ledger = Ledger()
        adapter = LiteLLMResponsesAdapter("synthetic", transport=httpx.MockTransport(http))
        model = GatewayResponsesModel(
            ProviderGateway(ledger, adapter), Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium")
        )
        try:
            with pytest.raises(RuntimeError, match="providerTransportFailed"):
                await Agent(model=model, output_type=NativeOutput(Output, strict=True)).run("text")
        finally:
            await adapter.close()
        assert len(requests) == len(ledger.calls) == 1
        assert requests[0]["text"]["format"]["strict"] is True

    asyncio.run(exercise())


def test_corrective_attempts_are_finite_and_isolated():
    async def exercise():
        requests = []

        def http(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=response("Incorrect language.", len(requests)))

        ledger = Ledger()
        adapter = LiteLLMResponsesAdapter("synthetic", transport=httpx.MockTransport(http))
        binding = Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium")
        agent = Agent(
            model=GatewayResponsesModel(ProviderGateway(ledger, adapter), binding),
            output_type=NativeOutput(Output, strict=True),
            retries={"output": 2},
        )

        @agent.output_validator
        def reject(data):
            raise ModelRetry("reply.language: expected es; detected en")

        try:
            with pytest.raises(Exception, match="retry|retries"):
                await agent.run("first check")
        finally:
            await adapter.close()
        assert len(requests) == len(ledger.calls) == 3
        assert [c["semantic"] for c in ledger.calls] == [1, 2, 3]

    asyncio.run(exercise())


def test_missing_usage_is_not_reported_as_zero():
    async def exercise():
        adapter = LiteLLMResponsesAdapter(
            "synthetic",
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=response("Respuesta en español.", 1, False))
            ),
        )
        ledger = Ledger()
        gateway = ProviderGateway(ledger, adapter)
        agent = Agent(
            model=GatewayResponsesModel(
                gateway, Binding(uuid4(), uuid4(), 1, "gpt-5.4-nano", "medium")
            ),
            output_type=NativeOutput(Output, strict=True),
        )
        try:
            await agent.run("A reply")
        finally:
            await adapter.close()
        observed = ledger.calls[0]["response"]
        assert observed.input_tokens is None and observed.output_tokens is None
        assert observed.reported_cost is None

    asyncio.run(exercise())
