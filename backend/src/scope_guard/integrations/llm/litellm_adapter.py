"""Pinned LiteLLM Responses transport, no hidden retries or inferred billing data."""

import logging

import httpx
import litellm
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from scope_guard.integrations.llm.gateway import ProviderResponse


def counter(value):
    return value if type(value) is int and value >= 0 else None


class ControlledHTTPHandler(AsyncHTTPHandler):
    """Use the pinned handler's client factory to inject a no-retry httpx client."""

    def __init__(self, client):
        self.injected_client = client
        super().__init__(timeout=60)

    def create_client(self, **kwargs):
        return self.injected_client


class LiteLLMResponsesAdapter:
    def __init__(self, key: str, *, transport=None):
        self.key = key
        self.client = httpx.AsyncClient(transport=transport, timeout=60)
        self.handler = ControlledHTTPHandler(self.client)
        litellm.num_retries = 0
        litellm.telemetry = False
        litellm.drop_params = False
        litellm.suppress_debug_info = True
        for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "httpx", "httpcore", "openai"):
            logging.getLogger(name).setLevel(logging.CRITICAL)

    async def close(self):
        await self.client.aclose()

    async def request(self, request, timeout):
        result = await litellm.aresponses(
            model="openai/" + request.binding.model.removeprefix("openai/"),
            api_key=self.key,
            input=request.messages,
            text={
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.schema,
                }
            },
            reasoning={"effort": request.binding.effort},
            max_output_tokens=request.max_output_tokens,
            timeout=timeout,
            num_retries=0,
            max_retries=0,
            client=self.handler,
            drop_params=False,
            store=False,
        )
        raw = result.model_dump()
        headers = (getattr(result, "_hidden_params", {}) or {}).get("headers") or {}
        usage = raw.get("usage") or {}
        chunks = [
            part.get("text", "")
            for item in raw.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
        return ProviderResponse(
            text="".join(chunks),
            model=raw.get("model"),
            provider="openai",
            response_id=raw.get("id"),
            request_id=headers.get("x-request-id"),
            status=raw.get("status") or "unknown",
            input_tokens=counter(usage.get("input_tokens")),
            output_tokens=counter(usage.get("output_tokens")),
            cached_tokens=counter((usage.get("input_tokens_details") or {}).get("cached_tokens")),
            reasoning_tokens=counter(
                (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
            ),
        )
