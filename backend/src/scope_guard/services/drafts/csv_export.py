"""Flat, localized current-Draft CSV. No persistence or generation side effects."""

import csv
import io
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Literal

HEADERS = {
    "en": (
        "Draft ID",
        "Project ID",
        "Project name",
        "Draft created at (UTC)",
        "Draft updated at (UTC)",
        "Draft revision",
        "Current client request",
        "Analysis verdict",
        "Analysis explanation",
        "Analysis is stale",
        "Selected client reply",
        "Client-material language",
        "Additional-work description",
        "Estimated hours",
        "Additional amount",
        "Currency",
        "Without additional payment",
        "Schedule change",
    ),
    "ru": (
        "ID черновика",
        "ID проекта",
        "Название проекта",
        "Черновик создан (UTC)",
        "Черновик изменён (UTC)",
        "Ревизия черновика",
        "Текущий запрос клиента",
        "Результат анализа",
        "Объяснение анализа",
        "Анализ устарел",
        "Выбранный ответ клиенту",
        "Язык материалов для клиента",
        "Описание дополнительных работ",
        "Оценка часов",
        "Сумма за дополнительные работы",
        "Валюта",
        "Без дополнительной оплаты",
        "Изменение сроков",
    ),
}
VERDICTS = {
    "en": {"in_scope": "In scope", "borderline": "Borderline", "out_of_scope": "Out of scope"},
    "ru": {
        "in_scope": "Входит в объём работ",
        "borderline": "Спорный случай",
        "out_of_scope": "Выходит за рамки работ",
    },
}


def spreadsheet_text(value) -> str:
    if value is None:
        return ""
    source = str(value)
    for character in source:
        if character.isspace() or unicodedata.category(character) in ("Cc", "Cf"):
            continue
        return "'" + source if character in "=+-@" else source
    return source


def timestamp(value) -> str:
    if not value:
        return ""
    instant = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


def render_drafts_csv(rows: Iterable[dict], locale: Literal["en", "ru"]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";" if locale == "ru" else ",", lineterminator="\r\n")
    writer.writerow(HEADERS[locale])

    def boolean(value):
        if value is None:
            return ""
        return ("Yes" if value else "No") if locale == "en" else ("Да" if value else "Нет")

    for draft in rows:
        analysis = draft.get("analysisResult") or {}
        document = draft.get("draftDocument") or {}
        reply = document.get("reply") or {}
        order = document.get("changeOrder") or {}
        writer.writerow(
            map(
                spreadsheet_text,
                (
                    draft.get("id"),
                    draft.get("projectId"),
                    draft.get("projectName"),
                    timestamp(draft.get("createdAt")),
                    timestamp(draft.get("updatedAt")),
                    draft.get("revision"),
                    draft.get("requestText"),
                    VERDICTS[locale].get(analysis.get("verdict") or "", ""),
                    analysis.get("reasoning"),
                    boolean(draft.get("analysisIsStale")),
                    reply.get("text"),
                    reply.get("language"),
                    order.get("description"),
                    order.get("estimatedHours"),
                    order.get("additionalCost"),
                    order.get("currency"),
                    boolean(order.get("noAdditionalCharge")),
                    order.get("timelineImpact"),
                ),
            )
        )
    return output.getvalue().encode("utf-8-sig")
