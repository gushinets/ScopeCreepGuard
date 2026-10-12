import re

from scope_guard.domain.projects.domain import ManualHistoryInput
from scope_guard.domain.shared.enums import Verdict
from scope_guard.domain.shared.errors import ValidationError
from scope_guard.domain.shared.js_compat import trim


def parse_history(body: dict) -> ManualHistoryInput:
    value = body.get("date")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValidationError("errors.historyDateInvalid")
    request = body.get("request")
    if not isinstance(request, str) or not trim(request):
        raise ValidationError("errors.requestRequired")
    verdict = body.get("verdict")
    if verdict not in ("in_scope", "borderline", "out_of_scope"):
        raise ValidationError("errors.verdictInvalid")
    summary = body.get("summary")
    if not isinstance(summary, str) or not trim(summary):
        raise ValidationError("errors.summaryRequired")
    return ManualHistoryInput(value, trim(request), Verdict(verdict), trim(summary))
