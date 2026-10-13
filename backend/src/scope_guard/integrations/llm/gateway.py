"""The sole transport retry owner; every dispatch has an independently durable ledger row."""

import asyncio
from datetime import UTC, datetime

from scope_guard.domain.llm.runtime import Binding as Binding
from scope_guard.domain.llm.runtime import GatewayFailure as GatewayFailure
from scope_guard.domain.llm.runtime import ProviderRequest as ProviderRequest
from scope_guard.domain.llm.runtime import ProviderResponse as ProviderResponse


class ProviderGateway:
    def __init__(self, ledger, adapter, *, sleep=asyncio.sleep):
        self.ledger, self.adapter, self.sleep = ledger, adapter, sleep

    async def validation_feedback(self, binding, message):
        await self.ledger.feedback(binding, {"rule": message[:500]})

    async def request(self, request: ProviderRequest) -> ProviderResponse:
        for attempt in range(request.binding.transport_start + 1, 3):
            remaining = min(request.timeout, 60)
            if request.binding.deadline:
                remaining = min(
                    remaining, (request.binding.deadline - datetime.now(UTC)).total_seconds()
                )
            if remaining <= 0:
                raise GatewayFailure("operationDeadlineExceeded")
            identifier = await self.ledger.reserve(request, attempt)
            try:
                async with asyncio.timeout(remaining):
                    response = await self.adapter.request(request, remaining)
            except BaseException as error:
                uncertain = isinstance(
                    error, (asyncio.CancelledError, TimeoutError, ConnectionError)
                ) or (
                    getattr(error, "status_code", None) == 408
                    or type(error).__name__
                    in ("Timeout", "APIConnectionError", "ReadTimeout", "ConnectError")
                )
                code = "providerOutcomeUnknown" if uncertain else "providerTransportFailed"
                await asyncio.shield(
                    self.ledger.complete(
                        identifier,
                        error={
                            "code": code,
                            "uncertain": uncertain,
                            "status": getattr(error, "status_code", None),
                        },
                    )
                )
                if isinstance(error, asyncio.CancelledError):
                    raise
                status = getattr(error, "status_code", 0) or 0
                retryable = (
                    isinstance(error, (TimeoutError, ConnectionError))
                    or status in (408, 409, 429)
                    or status >= 500
                )
                if not retryable or attempt == 2:
                    raise GatewayFailure(code) from None
                await self.sleep(min(0.5 * attempt, max(0, remaining)))
                continue
            await self.ledger.complete(identifier, response=response)
            await self.ledger.checkpoint(request, response)
            return response
        raise GatewayFailure("transportAttemptsExhausted")
