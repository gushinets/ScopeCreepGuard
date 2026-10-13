"""Offline language evidence; thresholds are policy defaults, not accuracy guarantees."""

import re
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder

from scope_guard.domain.change_orders.constants import SUPPORTED_LANGUAGES
from scope_guard.domain.shared.language import supported_language

VERSION = "lingua-2.1.1-policy-v1"


@lru_cache(maxsize=1)
def detector():
    languages = [
        language
        for language in Language.all()
        if language.iso_code_639_1.name.lower() in SUPPORTED_LANGUAGES
    ]
    return LanguageDetectorBuilder.from_languages(*languages).build()


def clean(text, exceptions=()):
    for value in sorted(exceptions, key=len, reverse=True):
        if value:
            text = text.replace(value, " ")
    return re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+\.[a-z]+", " ", text)


def evidence(text, exceptions=()):
    prose = clean(text, exceptions)
    if sum(c.isalpha() for c in prose) < 12:
        return {"language": None, "confidence": None, "status": "uncertain"}
    values = detector().compute_language_confidence_values(prose)
    if not values:
        return {"language": None, "confidence": None, "status": "uncertain"}
    first, second = values[0], values[1]
    language = first.language.iso_code_639_1.name.lower()
    dominant = detector().detect_multiple_languages_of(prose)
    total = sum(item.end_index - item.start_index for item in dominant)
    selected = sum(
        item.end_index - item.start_index for item in dominant if item.language == first.language
    )
    # Lingua may label shared vocabulary as another related language. Count a foreign
    # span only when that span independently meets the same confidence/margin policy.
    for item in dominant:
        if item.language == first.language:
            continue
        span = prose[item.start_index : item.end_index]
        alternatives = detector().compute_language_confidence_values(span)
        strong = (
            sum(c.isalpha() for c in span) >= 12
            and alternatives
            and alternatives[0].language == item.language
            and alternatives[0].value >= 0.80
            and alternatives[0].value - alternatives[1].value >= 0.20
        )
        if not strong:
            selected += item.end_index - item.start_index
    confident = (
        first.value >= 0.80
        and first.value - second.value >= 0.20
        and (not total or selected / total >= 0.75)
    )
    return {
        "language": language,
        "confidence": round(first.value, 4),
        "status": "detected" if confident else "uncertain",
    }


def select(request, locale, override=None):
    observed = evidence(request)
    language = supported_language(override)
    if override and not language:
        raise ValueError("clientLanguageInvalid")
    target = language or (observed["language"] if observed["status"] == "detected" else locale)
    return {
        **observed,
        "selectedLanguage": target,
        "override": language is not None,
        "version": VERSION,
    }
