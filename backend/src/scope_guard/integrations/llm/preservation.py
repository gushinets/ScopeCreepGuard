"""Saved translation fee checks and existing recognized schedule bindings."""

import re
from collections import Counter
from decimal import Decimal

from scope_guard.domain.llm.commercial_terms import current_commercial_terms
from scope_guard.integrations.llm.terms import mentions, normalize_number_words, preserve_mentions


def validate_translation_commercial_terms(stage, candidate, facts):
    """Pre-acceptance guard using the existing localized amount/unit recognizer.

    Only translation fees are blocking here. Other content remains subject to the
    existing diagnostics; this does not turn those observations into global retries.
    Saved prose can predate an explicit conversion or amount edit, so its old fee
    is a wording reference, never an alternative allowed payable amount.
    """
    if facts.get("action") != "translate" or stage not in ("replies", "change_order"):
        return
    terms = current_commercial_terms(facts)
    amount, currency = terms.get("additionalCost"), terms.get("currency")
    free = terms["noAdditionalCharge"]
    payable = amount not in (None, "") and bool(currency) and not free
    expected = (currency, Decimal(str(amount))) if payable else None
    document = facts["document"]
    reply = document["reply"]
    target = facts["selection"]["selectedLanguage"]
    fields = (
        ("warm", "neutral", "firm")
        if stage == "replies"
        else (
            "description",
            "timelineImpact",
            "rationale",
            "note",
            "additionalTerms",
        )
    )
    for field in fields:
        source = (
            (reply["text"] if field == reply["tone"] else reply["generated"][field])
            if stage == "replies"
            else document["changeOrder"].get(field, "")
        )
        translated = candidate[field]
        if not source.strip() and translated.strip():
            raise ValueError(f"{field}.commercial_terms: preserve cleared saved text fields")
        observed = {
            pair: count
            for pair, count in mentions(translated, target).items()
            if pair[0] != "hours"
        }
        original = {
            pair: count
            for pair, count in mentions(source, reply["language"]).items()
            if pair[0] != "hours"
        }
        if payable and any(pair != expected for pair in original):
            # A differing source amount may be an old total OR a saved deposit.
            # Resolve its role contextually; historical amount equality cannot do it.
            continue
        invalid = next(
            (
                pair
                for pair in observed
                if pair != expected and not (free and pair == (currency, Decimal(0)))
            ),
            None,
        )
        if invalid:
            stated_currency, stated_amount = invalid
            saved = (
                f"{amount} {currency}"
                if payable
                else ("no additional charge" if free else "empty (no saved payable fee)")
            )
            raise ValueError(
                f"{field}.commercial_terms: The saved payable amount is {saved}. "
                f"Your text states {stated_amount} {stated_currency}. "
                "Translate the text without changing the saved commercial terms."
            )
        if payable and sum(original.values()) != sum(observed.values()):
            raise ValueError(
                f"{field}.commercial_terms: Preserve fee mentions using the saved payable "
                f"amount {amount} {currency}; do not omit or add commercial terms."
            )


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


def preserve_translation(field, source, translated, source_language, target, *, money=True):
    if bool(source.strip()) != bool(translated.strip()):
        raise ValueError(f"{field}.preservation: preserve empty fields and saved text")
    preserve_mentions(field, source, translated, source_language, target, money=money)
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
