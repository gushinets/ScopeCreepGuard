"""Async Responses infrastructure. Logs contain only allowlisted metadata."""

import json
import logging
import time
from contextvars import ContextVar

from openai import AsyncOpenAI

from scope_guard.core.js_compat import stringify, trim
from scope_guard.infrastructure.llm.prompts.analysis_v1 import analysis_messages, reply_messages
from scope_guard.infrastructure.llm.prompts.client_materials_v1 import material_messages
from scope_guard.infrastructure.llm.retry import invoke
from scope_guard.infrastructure.llm.schemas import ANALYSIS_SCHEMA, MATERIALS_SCHEMA
from scope_guard.modules.analysis.domain import ABSENT, GenerationError
from scope_guard.modules.analysis.normalization import parse_analysis, parse_materials
from scope_guard.modules.analysis.serialization import analysis_to_wire

correlation_id: ContextVar[str] = ContextVar("generation_correlation_id", default="")
logger = logging.getLogger("scope_guard.generation")


class GenerationOpenAI(AsyncOpenAI):
    def _build_request(self, options, *, retries_taken=0):
        # The locked SDK encodes before httpx. Give it well-formed JSON bytes;
        # retain its authentication, transport, response parsing and proxies.
        if isinstance(options.json_data, dict) and options.extra_json is None:
            options = options.model_copy(
                update={"json_data": stringify(options.json_data).encode("utf-8")}
            )
        return super()._build_request(options, retries_taken=retries_taken)


def log_event(event: str, **fields):
    # Callers supply internal operation names and numeric/bounded metadata only.
    logger.info(
        json.dumps(
            {"event": event, "correlation_id": correlation_id.get(), **fields},
            separators=(",", ":"),
        )
    )


def analysis_fields(value, *, reply=False):
    p = value.context
    result = {
        "scope": p.scope,
        "request": value.request,
        "industry": p.industry,
        "locale": value.locale,
    }
    if reply:
        result.update(tone=value.tone, previousReply=value.previous_reply)
    else:
        result.update(
            pricingModel=p.pricing_model,
            currency=p.currency,
            hourlyRate=p.hourly_rate,
            fixedPrice=p.fixed_price,
            startDate=p.start_date,
        )
        if value.end_date is not None:
            result["endDate"] = value.end_date
        if value.draft_created_at is not None:
            result["draftCreatedAt"] = value.draft_created_at
    if value.document_language is not None:
        result["documentLanguage"] = value.document_language
    return result


class OpenAIGeneration:
    def __init__(self, key: str, *, client=None):
        self._key = key
        self._client = client

    async def close(self):
        if self._client is not None and hasattr(self._client, "close"):
            await self._client.close()

    async def _request(self, operation, messages, schema, name, effort):
        if not trim(self._key):
            raise GenerationError("analysisUnavailable", 503)
        if self._client is None:
            # httpx honours HTTP(S)_PROXY/NO_PROXY; no frontend environment loading.
            self._client = GenerationOpenAI(
                api_key=self._key,
                max_retries=0,
                timeout=600,
            )
        attempts = 0
        start = time.monotonic()

        def count(value):
            nonlocal attempts
            attempts = value

        try:
            response = await invoke(
                lambda: self._client.responses.create(
                    model="gpt-5.4-nano",
                    reasoning={"effort": effort},
                    **messages,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": name,
                            "strict": True,
                            "schema": schema,
                        }
                    },
                ),
                on_attempt=count,
            )
        except Exception:
            log_event(
                "provider_failed",
                operation=operation,
                attempts=attempts,
                category="provider",
                status=502,
            )
            raise GenerationError("analysisFailed", 502) from None
        fields = {
            "operation": operation,
            "correlation_id": correlation_id.get(),
            "attempts": attempts,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
        provider_id = getattr(response, "_request_id", None)
        if (
            isinstance(provider_id, str)
            and len(provider_id) <= 128
            and all(c.isalnum() or c in "_-" for c in provider_id)
        ):
            fields["provider_request_id"] = provider_id
        usage = getattr(response, "usage", None)
        if usage:
            for name in ("input_tokens", "output_tokens"):
                value = getattr(usage, name, None)
                if type(value) is int and value >= 0:
                    fields[name] = value
            reasoning = getattr(
                getattr(usage, "output_tokens_details", None), "reasoning_tokens", None
            )
            if type(reasoning) is int and reasoning >= 0:
                fields["reasoning_tokens"] = reasoning
        log_event("provider_completed", **fields)
        return response

    def _content(self, response):
        if (
            response.status != "completed"
            or not isinstance(response.output_text, str)
            or not trim(response.output_text)
        ):
            raise GenerationError("analysisFailed", 502)
        return response.output_text

    def _analysis(self, response, value):
        content = self._content(response)
        try:
            return parse_analysis(
                json.loads(content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())),
                value.locale,
                value.document_language,
            )
        except (ValueError, TypeError, KeyError):
            raise GenerationError("analysisInvalid", 502) from None

    async def analyze(self, value):
        system, user = analysis_messages(analysis_fields(value))
        response = await self._request(
            "analyze",
            {"instructions": system["content"], "input": user["content"]},
            ANALYSIS_SCHEMA,
            "scope_analysis",
            "medium",
        )
        return self._analysis(response, value)

    async def regenerate_reply(self, value):
        system, user = reply_messages(analysis_fields(value, reply=True))
        response = await self._request(
            "reply",
            {"instructions": system["content"], "input": user["content"]},
            ANALYSIS_SCHEMA,
            "scope_analysis",
            "high",
        )
        return getattr(self._analysis(response, value).replies, value.tone)

    async def translate_materials(self, value):
        messages = material_messages(
            {
                "scope": value.context.scope,
                "request": value.request,
                "locale": value.locale,
                "clientLanguage": value.client_language,
                "analysis": analysis_to_wire(value.analysis),
            }
        )
        response = await self._request(
            "materials", messages, MATERIALS_SCHEMA, "client_materials", "medium"
        )
        try:
            materials = parse_materials(json.loads(self._content(response)), value.client_language)
            applicable = value.analysis.verdict != "in_scope" and (
                value.analysis.has_additional_work
                if value.analysis.has_additional_work != ABSENT
                else value.analysis.verdict == "out_of_scope"
            )
            if applicable != (materials.change_order is not None):
                raise ValueError
            return materials
        except (ValueError, TypeError, GenerationError):
            raise GenerationError("analysisInvalid", 502) from None
