"""Exact pre-cutover messages; templates preserve runtime LF/spacing."""

from pathlib import Path

from scope_guard.core.js_compat import stringify
from scope_guard.infrastructure.llm.language import normalize_language
from scope_guard.modules.change_orders.estimation import project_timing
from scope_guard.modules.change_orders.schemas import LABEL_KEYS

SYSTEM = Path(__file__).with_name("analysis-system-v1.txt").read_text(encoding="utf8")
USER = Path(__file__).with_name("analysis-user-v1.txt").read_text(encoding="utf8")
REPLY = Path(__file__).with_name("reply-regeneration-v1.txt").read_text(encoding="utf8")


def render(template, replacements):
    # One substitution pass: untrusted input cannot introduce another placeholder.
    import re

    return re.sub(r"@@[A-Z_]+@@", lambda match: replacements[match[0]], template)


def analysis_messages(value: dict) -> list[dict]:
    language = {"en": "English", "ru": "Russian"}[value["locale"]]
    override = normalize_language(value.get("documentLanguage"))
    terms = {
        key: value.get(key)
        for key in ("pricingModel", "currency", "hourlyRate", "fixedPrice", "startDate")
    }
    if value.get("startDate") and value.get("draftCreatedAt"):
        terms.update(
            project_timing(value["startDate"], value.get("endDate"), value["draftCreatedAt"])
        )
    replacements = {
        "@@LANGUAGE@@": language,
        "@@LOCALE@@": value["locale"],
        "@@OVERRIDE_OR_ABSENT@@": override or "absent",
        "@@LABEL_KEYS@@": ", ".join(LABEL_KEYS),
        "@@INDUSTRY@@": value["industry"],
        "@@SCOPE@@": value["scope"],
        "@@REQUEST@@": value["request"],
        "@@TERMS@@": stringify(terms),
        "@@OVERRIDE_SENTENCE@@": f"CLIENT MATERIAL LANGUAGE OVERRIDE: {override}. The user explicitly selected this language for all replies and Change Order material."  # noqa: E501 - frozen compatibility literal
        if override
        else "",
    }
    return [
        {"role": "system", "content": render(SYSTEM, replacements)},
        {"role": "user", "content": render(USER, replacements)},
    ]


def reply_messages(value: dict) -> list[dict]:
    messages = analysis_messages(value)
    suffix = render(
        REPLY,
        {
            "@@TONE@@": value["tone"],
            "@@TONE_UPPER@@": value["tone"].upper(),
            "@@PREVIOUS@@": value["previousReply"],
        },
    )
    return [messages[0], {"role": "user", "content": messages[1]["content"] + "\n\n" + suffix}]
