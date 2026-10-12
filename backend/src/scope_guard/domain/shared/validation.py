import re
from datetime import date


def iso_date(value: object) -> object:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid_date")
    return date.fromisoformat(value)


def language_tag(value: str) -> str:
    # Canonical language selection belongs to the generation adapter (ANY-640).
    # Contracts accept bounded tags, never prompt text, and preserve saved casing.
    value = value.strip()
    if len(value) > 100 or not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", value):
        raise ValueError("invalid_language")
    if value.split("-")[0].lower() in {"other", "und", "zxx", "mul"}:
        raise ValueError("invalid_language")
    return value
