"""Legacy ordered validation. Presence is retained independently of JSON null."""

import re
from typing import Literal, cast

from scope_guard.core.js_compat import stringify, trim, utf16_length
from scope_guard.infrastructure.llm.language import normalize_language, supported_language
from scope_guard.modules.analysis.domain import (
    ABSENT,
    AnalyzeCommand,
    EstimateCommand,
    GenerationError,
    HistoricalSelector,
    MaterialsCommand,
    RegenerateReplyCommand,
    freeze,
)

MAX_CHARS = 100_000


def valid_date(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    year, month, day = map(int, value.split("-"))
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return 1 <= month <= 12 and 1 <= day <= days[month - 1]


def end_date(body: dict) -> str | None:
    if "endDate" in body and not valid_date(body["endDate"]):
        raise GenerationError("requestBodyInvalid")
    return body.get("endDate")


def language(body: dict, broad=False) -> str | None:
    result = (normalize_language if broad else supported_language)(body.get("documentLanguage"))
    if "documentLanguage" in body and not result:
        raise GenerationError("requestBodyInvalid" if broad else "clientLanguageUnsupported")
    return result


def required(body: dict, key: str, error="requestBodyInvalid", nonblank=True, trimmed=True) -> str:
    value = body.get(key)
    if not isinstance(value, str) or (nonblank and not trim(value)):
        raise GenerationError(error)
    return trim(value) if trimmed else value


def selector(body: dict) -> HistoricalSelector:
    return HistoricalSelector(
        *(freeze(body.get(key, ABSENT)) for key in ("draftId", "proof", "locale"))
    )


def parse_analyze(body: dict) -> AnalyzeCommand:
    override = language(body)
    project = required(body, "projectId")
    request = required(body, "request", "requestRequired")
    return AnalyzeCommand(project, request, end_date(body), override)


def parse_reply(body: dict) -> RegenerateReplyCommand:
    override = language(body, broad=True)
    project = required(body, "projectId")
    request = required(body, "request", "requestRequired")
    tone = body.get("tone")
    if tone not in ("warm", "neutral", "firm"):
        raise GenerationError("requestBodyInvalid")
    previous = required(body, "previousReply")
    if max(utf16_length(request), utf16_length(previous)) > MAX_CHARS:
        raise GenerationError("analysisInputTooLarge")
    return RegenerateReplyCommand(
        project, request, cast(Literal["warm", "neutral", "firm"], tone), previous, override
    )


def parse_materials(body: dict) -> MaterialsCommand:
    project = required(body, "projectId", nonblank=False, trimmed=False)
    if "historyId" in body and not isinstance(body["historyId"], str):
        raise GenerationError("requestBodyInvalid")
    request = required(body, "request", nonblank=False, trimmed=False)
    target = supported_language(body.get("clientLanguage"))
    if not target:
        raise GenerationError("clientLanguageUnsupported")
    raw = {"request": request, "clientLanguage": target}
    if "analysis" in body:
        raw["analysis"] = body["analysis"]
    size = utf16_length(stringify(raw))
    if size > MAX_CHARS:
        raise GenerationError("analysisInputTooLarge")
    return MaterialsCommand(
        project,
        request,
        target,
        freeze(body.get("analysis", ABSENT)),
        size,
        selector(body),
        body.get("historyId", ABSENT),
    )


def parse_estimate(body: dict) -> EstimateCommand:
    project = required(body, "projectId", nonblank=False, trimmed=False)
    request = required(body, "request", trimmed=False)
    date = end_date(body)
    override = language(body)
    return EstimateCommand(project, request, selector(body), date, override)
