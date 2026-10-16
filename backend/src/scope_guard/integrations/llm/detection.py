"""Offline language evidence; thresholds are policy defaults, not accuracy guarantees."""

import re
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder

from scope_guard.domain.change_orders.constants import SUPPORTED_LANGUAGES
from scope_guard.domain.shared.language import supported_language

VERSION = "lingua-2.1.1-input-v2-output-v2"

# Neutral technical nouns/product identifiers in input, not natural-language votes.
# Finite calibration vocabulary; unknown terms still contribute uncertainty.
TECHNICAL_INPUT = re.compile(
    r"\b(?:email|e-mail|frontend|backend|fullstack|webhooks?|endpoints?|"
    r"PostgreSQL|MySQL|MongoDB|Docker|Kubernetes|Arrow|DigiKey|Mouser|"
    r"Instagram|Facebook|Salesforce|WordPress|OpenAI|GitHub|JavaScript|TypeScript|"
    r"Python|React|Next\.js|OAuth|REST|GraphQL|SDK|CI/CD)\b",
    re.I,
)


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
    # Detection-only representation. Never use this to rewrite model/source inputs.
    text = re.sub(
        r"```[\s\S]*?```|https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[a-z]+", " ", text, flags=re.I
    )
    text = re.sub(
        r"`[^`\n]*`", lambda m: " " if re.search(r"[_(){}=;]|[a-z][A-Z]", m[0]) else m[0], text
    )
    text = re.sub(r"\b(?:[a-z]+(?:[A-Z][a-z0-9]*)+|[a-z]+(?:_[a-z0-9]+)+)\b", " ", text)
    return re.sub(r"\b(?:API|URL|HTTP|HTTPS|JSON|SQL|SEO|webhooks?)\b", " ", text, flags=re.I)


def fragments(prose):
    sentences = re.split(r"[.!?;\n]+\s*", prose)
    return [
        *sentences,
        *(
            prose[s.start_index : s.end_index]
            for s in detector().detect_multiple_languages_of(prose)
        ),
    ]


def foreign_evidence(text, target):
    """Independent strong foreign evidence cannot borrow majority confidence."""
    for span in fragments(text):
        observed = evidence(span, minimum_letters=8)
        if observed["status"] == "detected" and observed["language"] != target:
            return observed
    return None


def input_evidence(text):
    prose = TECHNICAL_INPUT.sub(" ", clean(text))
    # Nonoverlapping Lingua spans provide relative volume. Independently score each
    # substantive span; sentence boundaries prevent a short second language being
    # swallowed into the whole-text score. Uncertain volume stays in the denominator.
    totals, confidences, volume = {}, {}, 0
    for sentence in re.split(r"[.!?;\n]+\s*", prose):
        whole = evidence(sentence, confidence_threshold=0.75)
        if whole["status"] == "detected" and not foreign_evidence(sentence, whole["language"]):
            letters = sum(c.isalpha() for c in sentence)
            volume += letters
            language = whole["language"]
            totals[language] = totals.get(language, 0) + letters
            confidences[language] = min(confidences.get(language, 1), whole["confidence"])
            continue
        spans = detector().detect_multiple_languages_of(sentence)
        for span in spans:
            part = sentence[span.start_index : span.end_index]
            letters = sum(c.isalpha() for c in part)
            volume += letters
            observed = evidence(part, confidence_threshold=0.75)
            if observed["status"] == "detected":
                language = observed["language"]
                totals[language] = totals.get(language, 0) + letters
                confidences[language] = min(confidences.get(language, 1), observed["confidence"])
    if totals:
        leading = max(totals, key=totals.get)
        share = totals[leading] / volume
        if share >= 0.65:
            return {"language": leading, "confidence": confidences[leading], "status": "detected"}
    observed = evidence(prose)
    return {**observed, "status": "uncertain"}


def evidence(text, exceptions=(), *, minimum_letters=12, confidence_threshold=0.80):
    prose = clean(text, exceptions)
    if sum(c.isalpha() for c in prose) < minimum_letters:
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
        first.value >= confidence_threshold
        and first.value - second.value >= 0.20
        and (not total or selected / total >= 0.75)
    )
    return {
        "language": language,
        "confidence": round(first.value, 4),
        "status": "detected" if confident else "uncertain",
    }


def select(request, locale, override=None):
    observed = input_evidence(request)
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
