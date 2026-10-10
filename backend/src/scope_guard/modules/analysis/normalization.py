"""Legacy runtime normalization, distinct from the strict provider output schema."""

import math
import re
from dataclasses import replace
from typing import NoReturn

from scope_guard.core.js_compat import date_parse_finite, js_string, trim, utf16_length
from scope_guard.infrastructure.llm.language import normalize_language, supported_language
from scope_guard.modules.analysis.domain import (
    ABSENT,
    Absent,
    AnalysisResult,
    ChangeOrder,
    ClientChangeOrder,
    ClientMaterials,
    Labels,
    Replies,
)
from scope_guard.modules.change_orders.schemas import LABEL_KEYS


def invalid(reason: str) -> NoReturn:
    raise ValueError("invalid_analysis_result:" + reason)


def obj(value, reason):
    if not isinstance(value, dict):
        invalid(reason)
    return value


def text(value, reason):
    if not isinstance(value, str) or not trim(value):
        invalid(reason)
    return trim(value)


def finite_number(value) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def labels(value) -> Labels | Absent:
    if not isinstance(value, dict):
        return ABSENT
    if not all(
        isinstance(value.get(key), str)
        and trim(value[key])
        and utf16_length(value[key]) <= 1500
        and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value[key])
        for key in LABEL_KEYS
    ):
        return ABSENT
    return Labels(tuple((key, trim(value[key])) for key in LABEL_KEYS))


def parse_analysis(value, locale="en", override=None) -> AnalysisResult:
    raw = obj(value, "not_object")
    language = (
        normalize_language(override)
        or normalize_language(raw.get("clientLanguage", raw.get("requestLanguage")))
        or locale
    )
    translated_labels = labels(raw.get("changeOrderLabels"))
    if language.split("-")[0] not in {"ru", "en", "es"} and translated_labels == ABSENT:
        invalid("changeOrderLabels")
    if override and normalize_language(raw.get("clientLanguage")) != language:
        invalid("clientLanguage_override")
    if raw.get("verdict") not in {"in_scope", "borderline", "out_of_scope"}:
        invalid("verdict")
    confidence = raw.get("confidence")
    if not finite_number(confidence) or confidence != int(confidence) or not 0 <= confidence <= 100:
        invalid("confidence")
    summary, reasoning = (
        text(raw.get("summary"), "summary"),
        text(raw.get("reasoning"), "reasoning"),
    )
    citations = raw.get("citations")
    if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
        invalid("citations")
    if "suggestion" in raw and not isinstance(raw["suggestion"], str):
        invalid("suggestion")
    reply = obj(raw.get("replies"), "replies")
    replies = Replies(
        *(text(reply.get(tone), "replies." + tone) for tone in ("warm", "neutral", "firm"))
    )
    co = obj(raw.get("changeOrder"), "changeOrder")
    if "hasAdditionalWork" in raw and type(raw["hasAdditionalWork"]) is not bool:
        invalid("hasAdditionalWork")
    if "requestLanguage" in raw and js_string(raw["requestLanguage"]) not in {
        "ru",
        "en",
        "es",
        "other",
    }:
        invalid("requestLanguage")
    hours = co.get("estimatedHours", ABSENT)
    if hours != ABSENT and (not finite_number(hours) or hours < 0):
        invalid("changeOrder.estimatedHours")
    if "currency" in co and js_string(co["currency"]) not in {"", "RUB", "USD", "EUR"}:
        invalid("changeOrder.currency")
    if "rationale" in co and not isinstance(co["rationale"], str):
        invalid("changeOrder.rationale")
    cost = co.get("additionalCost")
    estimate_valid = (
        raw.get("hasAdditionalWork") is True
        and hours != ABSENT
        and hours > 0
        and bool(re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", js_string(cost)))
        and float(cost) > 0
        and co.get("currency", ABSENT) != ""
        and isinstance(co.get("rationale"), str)
        and bool(trim(co["rationale"]))
    )
    change_order = ChangeOrder(
        text(co.get("description"), "changeOrder.description"),
        text(co.get("timelineImpact"), "changeOrder.timelineImpact"),
        text(cost, "changeOrder.additionalCost"),
        text(co.get("note"), "changeOrder.note"),
        hours,
        co.get("currency", ABSENT) if isinstance(co.get("currency"), str) else ABSENT,
        co.get("rationale", ABSENT),
    )
    return AnalysisResult(
        raw["verdict"],
        int(confidence),
        summary,
        reasoning,
        tuple(citations),
        replies,
        change_order,
        language,
        translated_labels,
        raw.get("hasAdditionalWork", ABSENT),
        raw.get("requestLanguage", ABSENT)
        if isinstance(raw.get("requestLanguage"), str)
        else ABSENT,
        bool(estimate_valid) if "hasAdditionalWork" in raw else ABSENT,
        trim(raw["suggestion"])
        if isinstance(raw.get("suggestion"), str) and trim(raw["suggestion"])
        else ABSENT,
    )


def parse_snapshot(value, locale="en") -> AnalysisResult:
    raw = obj(value, "not_object")
    parsed = parse_analysis(raw, locale)
    if "changeOrderLabels" in raw and labels(raw["changeOrderLabels"]) == ABSENT:
        raise ValueError("invalid_draft_document")
    created = raw.get("draftCreatedAt", ABSENT)
    if created != ABSENT:
        if not isinstance(created, str) or not date_parse_finite(created):
            raise ValueError("invalid_draft_document")
    signature = raw.get("commercialSignature", ABSENT)
    if signature != ABSENT and (not isinstance(signature, str) or utf16_length(signature) > 100000):
        raise ValueError("invalid_draft_document")
    if "estimateValid" in raw and type(raw["estimateValid"]) is not bool:
        raise ValueError("invalid_draft_document")
    return replace(
        parsed,
        draft_created_at=created,
        commercial_signature=signature,
        estimate_valid=raw.get("estimateValid", parsed.estimate_valid),
    )


def parse_materials(value, expected=None) -> ClientMaterials:
    raw = obj(value, "client_materials")
    language = supported_language(raw.get("clientLanguage"))
    if not language or (expected and language != expected):
        invalid("client_materials_language")

    def content(value, empty=False):
        if (
            not isinstance(value, str)
            or utf16_length(value) > 100000
            or (not empty and not trim(value))
        ):
            invalid("client_materials_text")
        return value

    reply = obj(raw.get("replies"), "client_materials_replies")
    co = raw.get("changeOrder")
    translated = None
    if co is not None:
        co = obj(co, "client_materials_change_order")
        translated = ClientChangeOrder(
            content(co.get("description")),
            content(co.get("timelineImpact")),
            content(co.get("rationale"), True),
            content(co.get("note")),
        )
    translated_labels = labels(raw.get("changeOrderLabels"))
    if language.split("-")[0] not in {"ru", "en", "es"} and translated_labels == ABSENT:
        invalid("client_materials_labels")
    return ClientMaterials(
        language,
        Replies(*(content(reply.get(tone)) for tone in ("warm", "neutral", "firm"))),
        translated,
        translated_labels,
    )
