"""Only retry owner; matches the installed JavaScript SDK's admission and delays."""

import asyncio
import math
import random
import re
import time
from email.utils import parsedate_to_datetime

import openai


def should_retry(error):
    headers = getattr(getattr(error, "response", None), "headers", {})
    override = headers.get("x-should-retry")
    if override in ("true", "false"):
        return override == "true"
    return (
        isinstance(error, (openai.APIConnectionError, TimeoutError))
        or getattr(error, "status_code", 0) in (408, 409, 429)
        or getattr(error, "status_code", 0) >= 500
    )


def retry_delay(error, retry: int, *, clock=time.time, random_value=random.random):
    headers = getattr(getattr(error, "response", None), "headers", {})

    def parse_float(value):
        if not isinstance(value, str):
            return None
        match = re.match(
            r"\s*([+-]?(?:Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?))", value
        )
        return float(match[1]) if match else None

    delay = parse_float(headers.get("retry-after-ms"))
    if delay is not None:
        delay /= 1000
    value = headers.get("retry-after")
    # JS treats zero milliseconds as false and then consults Retry-After.
    if value and not delay:
        delay = parse_float(value)
        if delay is None:
            try:
                delay = parsedate_to_datetime(value).timestamp() - clock()
            except (TypeError, ValueError, AttributeError, OverflowError):
                delay = 0
    if delay is not None:
        # JS sleep treats past/invalid dates as immediate. Valid delays have no cap.
        return max(0, delay) if math.isfinite(delay) else 0
    return min(0.5 * 2**retry, 8) * (1 - random_value() * 0.25)


async def invoke(attempt, *, sleep=asyncio.sleep, on_attempt=None):
    for index in range(3):
        if on_attempt:
            on_attempt(index + 1)
        try:
            async with asyncio.timeout(600):
                return await attempt()
        except (openai.APIError, TimeoutError) as error:
            if index == 2 or not should_retry(error):
                raise
            await sleep(retry_delay(error, index))
    raise AssertionError("unreachable")
