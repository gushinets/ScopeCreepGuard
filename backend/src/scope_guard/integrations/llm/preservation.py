"""Deterministic recognized schedule bindings; contextual review covers other wording."""

import re
from collections import Counter

from scope_guard.integrations.llm.terms import normalize_number_words, preserve_mentions


def recognized_schedule_language(text, language):
    """Reviewed short schedule grammar, never a general prose confidence exemption."""
    base = language.split("-")[0]
    vocabulary = {
        "en": "working business calendar day days after following the approval within",
        "es": "días día laborables hábiles naturales calendario después de la aprobación tras",
        "ru": "рабочих рабочие рабочий рабочего календарных календарные "
        "календарный календарного день дня дней дни после "
        "согласования одобрения утверждения",
    }
    words = set(re.findall(r"[^\W\d_]+", normalize_number_words(text.casefold(), language)))
    return (
        bool(schedules(text, language))
        and bool(words)
        and words <= set(vocabulary.get(base, "").split())
    )


def schedules(text, language):
    text = normalize_number_words(text.casefold(), language)
    pattern = (
        r"\b(\d+)\s+(?:(working|business|calendar|рабоч(?:их|ие|ий|его)|календарн(?:ых|ые|ый|ого))\s+)?"
        r"(days?|weeks?|months?|день|дня|дней|дни|недел\w*|месяц\w*|días?|semanas?|meses?)"
        r"(?:\s+(laborables|hábiles|naturales|calendario))?\b"
    )
    result = Counter()
    for m in re.finditer(pattern, text):
        quantity, before, unit, after = m.groups()
        basis = before or after or "unspecified"
        basis = (
            "working"
            if basis.startswith(("working", "business", "рабоч", "labor", "hábil"))
            else "calendar"
            if basis.startswith(("calendar", "календар", "natural"))
            else basis
        )
        unit = (
            "days"
            if unit.startswith(("day", "дн", "ден", "dí"))
            else "weeks"
            if unit.startswith(("week", "нед", "seman"))
            else "months"
        )
        approval = bool(
            re.search(
                r"after\s+(?:the\s+)?approval|following\s+approval|después\s+de\s+la\s+aprobación|"
                r"tras\s+la\s+aprobación|после\s+(?:согласования|одобрения|утверждения)",
                text,
            )
        )
        result[(int(quantity), unit, basis, approval)] += 1
    return result


def preserve_translation(field, source, translated, source_language, target):
    if bool(source.strip()) != bool(translated.strip()):
        raise ValueError(f"{field}.preservation: preserve empty fields and saved text")
    preserve_mentions(field, source, translated, source_language, target)
    # Only compare this local grammar when both locales are covered. The single
    # persisted semantic review evaluates all other languages and complex schedules.
    if source_language.split("-")[0] in ("en", "ru", "es") and target.split("-")[0] in (
        "en",
        "ru",
        "es",
    ):
        if schedules(source, source_language) != schedules(translated, target):
            raise ValueError(
                f"{field}.timeline_commitment: preserve quantity, unit, "
                "working/calendar basis and start condition"
            )
