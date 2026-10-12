"""Versioned working-state rules. No transport or persistence dependencies."""

import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation

from scope_guard.domain.shared.language import normalize_language


class WorkflowError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code = "errors." + code
        self.status = status
        super().__init__(self.code)


def operation_hash(parameters: dict) -> str:
    encoded = json.dumps(
        parameters, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def empty_document(language: str = "en") -> dict:
    return {
        "version": 2,
        "reply": {
            "text": "",
            "tone": "neutral",
            "language": language,
            "generated": {"warm": "", "neutral": "", "firm": ""},
        },
        "changeOrder": None,
    }


def decimal_text(value, *, places: int = 2, optional: bool = True) -> str | None:
    if optional and value in (None, ""):
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise WorkflowError("documentInvalid")
    try:
        amount = Decimal(value)
        if (
            not amount.is_finite()
            or amount < 0
            or amount >= Decimal("1e12")
            or amount != amount.quantize(Decimal(1).scaleb(-places))
        ):
            raise WorkflowError("documentInvalid")
        return format(amount, f".{places}f")
    except InvalidOperation:
        raise WorkflowError("documentInvalid") from None


EDITOR_TEXT = {
    "description",
    "estimatedHours",
    "additionalCost",
    "timelineImpact",
    "rationale",
    "note",
    "providerName",
    "clientName",
    "clientEmail",
    "endDate",
    "additionalTerms",
    "clientApproverName",
    "approvalDate",
    "projectName",
    "createdAt",
    "reference",
}
EDITOR_KEYS = EDITOR_TEXT | {
    "language",
    "currency",
    "noAdditionalCharge",
    "changeOrderLabels",
    "aiValues",
}


def validate_document(value: dict) -> dict:
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "reply", "changeOrder"}
        or type(value["version"]) is not int
        or value["version"] != 2
    ):
        raise WorkflowError("documentInvalid")
    reply = value["reply"]
    if (
        not isinstance(reply, dict)
        or set(reply) != {"text", "tone", "language", "generated"}
        or reply.get("tone") not in ("warm", "neutral", "firm")
        or not isinstance(reply.get("text"), str)
        or not normalize_language(reply.get("language"))
    ):
        raise WorkflowError("documentInvalid")
    generated = reply["generated"]
    if (
        not isinstance(generated, dict)
        or set(generated) != {"warm", "neutral", "firm"}
        or not all(isinstance(v, str) for v in generated.values())
    ):
        raise WorkflowError("documentInvalid")
    co = value["changeOrder"]
    if co is not None:
        if (
            not isinstance(co, dict)
            or set(co) - EDITOR_KEYS
            or not normalize_language(co.get("language"))
            or type(co.get("noAdditionalCharge")) is not bool
            or co.get("currency") not in ("", "RUB", "USD", "EUR")
        ):
            raise WorkflowError("documentInvalid")
        if any(not isinstance(co[key], str) for key in EDITOR_TEXT & co.keys()):
            raise WorkflowError("documentInvalid")
        for key in ("additionalCost", "estimatedHours"):
            decimal_text(co.get(key))
        for key in ("endDate", "approvalDate"):
            if co.get(key):
                try:
                    date.fromisoformat(co[key])
                except (ValueError, TypeError):
                    raise WorkflowError("documentInvalid") from None
        for key in ("aiValues", "changeOrderLabels"):
            if key in co and (
                not isinstance(co[key], dict)
                or not all(isinstance(v, str) for v in co[key].values())
            ):
                raise WorkflowError("documentInvalid")
    if len(json.dumps(value, ensure_ascii=True)) > 1_000_000:
        raise WorkflowError("documentTooLarge", 413)
    return deepcopy(value)


def validate_agreement(value: dict) -> dict:
    if not isinstance(value, dict) or not str(value.get("description", "")).strip():
        raise WorkflowError("documentInvalid")
    result = deepcopy(value)
    result["estimatedHours"] = decimal_text(value.get("estimatedHours"))
    if value.get("noAdditionalCharge") is True:
        result["additionalCost"] = "0.00"
    else:
        result["additionalCost"] = decimal_text(value.get("additionalCost"), optional=False)
        if Decimal(result["additionalCost"]) <= 0:
            raise WorkflowError("documentInvalid")
    if value.get("currency") not in ("RUB", "USD", "EUR"):
        raise WorkflowError("documentInvalid")
    return result


def transition(kind: str, current: str, target: str) -> str:
    rules = {
        "analysis": {"pending": {"running"}, "running": {"succeeded", "failed", "cancelled"}},
        "export": {
            "pending": {"processing"},
            "processing": {"ready", "failed"},
            "failed": {"pending"},
            "ready": {"expired"},
        },
    }
    if target not in rules.get(kind, {}).get(current, set()):
        raise WorkflowError("invalidTransition", 409)
    return target


def analysis_matches(run: dict | None, request: str, context: dict) -> bool:
    return bool(
        run
        and run.get("status") == "succeeded"
        and run.get("projectSnapshot") is not None
        and run.get("requestText") == request
        and run["projectSnapshot"] == context
    )


SAVE_REASONS = {
    "autosave",
    "manual_save",
    "tone_change",
    "language_change",
    "regenerate",
    "change_order_edit",
    "restore",
    "clear",
    "analysis_apply",
    "project_change",
}
