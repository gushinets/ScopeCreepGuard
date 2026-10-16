import json
from datetime import date
from functools import lru_cache
from importlib.resources import files

from babel import Locale
from babel.dates import format_date

from scope_guard.domain.analysis.domain import ABSENT, Labels
from scope_guard.domain.change_orders.constants import LABEL_KEYS
from scope_guard.domain.shared.language import normalize_language
from scope_guard.services.documents.models import DocumentError

PDF_LANGUAGES = frozenset(
    "ru en es de fr it nl pl pt tr uk bg el cs sk hr ro hu fi sv da nb et lv lt id".split()
)


@lru_cache(maxsize=64)
def reviewed_stage_labels(language: str) -> dict[str, str] | None:
    """Complete server-owned native-contract labels for reviewed catalog locales."""
    catalog = json.loads(files(__package__).joinpath("labels.json").read_text(encoding="utf-8"))
    base = language.split("-")[0]
    if base not in catalog:
        return None
    aliases = {
        "draft": "status",
        "clientEmail": "email",
        "estimatedEffort": "effort",
        "additionalFee": "fee",
        "noAdditionalCharge": "noCharge",
    }
    result = {key: catalog[base][aliases.get(key, key)] for key in LABEL_KEYS if key != "hours"}
    result["hours"] = {"en": "hours", "ru": "часы", "es": "horas"}[base]
    return result


def supported_language(value: str) -> str:
    import re

    language = normalize_language(value)
    if not language or not re.fullmatch(
        r"[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-\d{3})?", language
    ):
        raise DocumentError("pdfLanguageUnsupported")
    parts = language.split("-")
    base = parts[0]
    script = "Cyrl" if base in ("ru", "uk", "bg") else "Grek" if base == "el" else "Latn"
    if base not in PDF_LANGUAGES or any(len(part) == 4 and part != script for part in parts[1:]):
        raise DocumentError("pdfLanguageUnsupported")
    return language


def document_date(value: str, language: str) -> str:
    try:
        day = date.fromisoformat(value[:10])
    except ValueError:
        return value
    try:
        locale = Locale.parse(language, sep="-")
    except (ValueError, LookupError):
        locale = Locale.parse(language.split("-")[0])
    return format_date(day, format="long", locale=locale).replace("\u202f", " ")


def document_labels(language: str, supplied: Labels | object = ABSENT) -> dict[str, str]:
    builtins = json.loads(files(__package__).joinpath("labels.json").read_text(encoding="utf-8"))
    base = language.split("-")[0]
    if base in builtins:
        return builtins[base]
    if not isinstance(supplied, Labels):
        raise DocumentError("pdfLabelsMissing")
    result = dict(supplied.values)
    for source, target in [
        ("draft", "status"),
        ("clientEmail", "email"),
        ("estimatedEffort", "effort"),
        ("additionalFee", "fee"),
        ("noAdditionalCharge", "noCharge"),
    ]:
        result[target] = result[source]
    return result
