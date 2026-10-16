"""Document readiness warnings, separate from project pricing and finalization rules."""

import re
from decimal import Decimal


def document_readiness(value):
    value = value or {}
    issues = {}
    for field in ("providerName", "clientName", "description"):
        if not str(value.get(field) or "").strip():
            issues[field] = "required"
    for field in ("estimatedHours", "additionalCost"):
        if field == "additionalCost" and value.get("noAdditionalCharge"):
            continue
        text = str(value.get(field) or "").strip()
        if not text:
            issues[field] = "required"
        elif (
            not re.fullmatch(r"\d+(?:\.\d{1,2})?", text)
            or Decimal(text) <= 0
            or Decimal(text) >= Decimal("1e12")
        ):
            issues[field] = "positive"
    if not value.get("noAdditionalCharge") and value.get("currency") not in ("USD", "EUR", "RUB"):
        issues["currency"] = "required"
    if not str(value.get("timelineImpact") or "").strip() and not value.get("endDate"):
        issues["timelineImpact"] = "required"
    return issues


def readiness_message(issues, language, labels):
    keys = {
        "providerName": "provider",
        "clientName": "client",
        "description": "requestedChange",
        "estimatedHours": "effort",
        "additionalCost": "fee",
        "currency": "fee",
        "timelineImpact": "scheduleImpact",
    }
    names = list(dict.fromkeys(labels[keys[field]] for field in issues))
    if not names:
        return ""
    prefix = {
        "en": "Incomplete draft — complete or correct",
        "ru": "Неполный черновик — заполните или исправьте",
        "es": "Borrador incompleto — completar o corregir",
    }.get(language.split("-")[0], "⚠ " + labels["status"])
    return prefix + ": " + "; ".join(names)
