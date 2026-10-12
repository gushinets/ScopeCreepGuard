import re

from scope_guard.api.errors import ApiError, ErrorCode
from scope_guard.api.project_input import trim
from scope_guard.core.contracts import Verdict
from scope_guard.domain.projects.domain import ManualHistoryInput


def parse_history(body: dict) -> ManualHistoryInput:
    value = body.get("date")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ApiError(ErrorCode.history_date_invalid)
    request = body.get("request")
    if not isinstance(request, str) or not trim(request):
        raise ApiError(ErrorCode.request_required)
    verdict = body.get("verdict")
    if verdict not in ("in_scope", "borderline", "out_of_scope"):
        raise ApiError(ErrorCode.verdict_invalid)
    summary = body.get("summary")
    if not isinstance(summary, str) or not trim(summary):
        raise ApiError(ErrorCode.summary_required)
    return ManualHistoryInput(value, trim(request), Verdict(verdict), trim(summary))
