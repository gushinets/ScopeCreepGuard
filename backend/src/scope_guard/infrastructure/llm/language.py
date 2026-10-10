"""BCP47 canonicalization; replies retain the wider language surface."""

import re

from langcodes import Language

from scope_guard.core.js_compat import trim, utf16_length
from scope_guard.modules.change_orders.schemas import SUPPORTED_LANGUAGES


def intl_structure(raw: str) -> str | None:
    """Unicode locale identifiers: Intl excludes extlangs/grandfathered tags."""
    parts = raw.lower().split("-")
    if not re.fullmatch(r"[a-z]{2,3}|[a-z]{5,8}", parts[0]):
        return None
    index = 1
    if index < len(parts) and re.fullmatch(r"[a-z]{4}", parts[index]):
        index += 1
    if index < len(parts) and re.fullmatch(r"[a-z]{2}|[0-9]{3}", parts[index]):
        index += 1
    variants = set()
    while index < len(parts) and len(parts[index]) != 1:
        part = parts[index]
        if not re.fullmatch(r"[a-z0-9]{5,8}|[0-9][a-z0-9]{3}", part) or part in variants:
            return None
        variants.add(part)
        index += 1
    base = parts[:index]
    extensions = {}
    private = []
    while index < len(parts):
        singleton = parts[index]
        if singleton in extensions or singleton == "x":
            if singleton != "x":
                return None
            private = parts[index:]
            if len(private) == 1:
                return None
            break
        index += 1
        start = index
        while index < len(parts) and len(parts[index]) != 1:
            index += 1
        values = parts[start:index]
        if not values or any(len(part) < 2 for part in values):
            return None
        if singleton == "u":
            attributes = set()
            offset = 0
            while offset < len(values) and len(values[offset]) >= 3:
                attributes.add(values[offset])
                offset += 1
            keywords: dict[str, list[str]] = {}
            while offset < len(values):
                key = values[offset]
                if not re.fullmatch(r"[a-z0-9][a-z]", key):
                    return None
                offset += 1
                start = offset
                while offset < len(values) and len(values[offset]) >= 3:
                    offset += 1
                keywords.setdefault(key, values[start:offset])
            values = sorted(attributes)
            for key, content in sorted(keywords.items()):
                aliases = {
                    ("ca", "islamicc"): "islamic-civil",
                    ("ms", "imperial"): "uksystem",
                    ("tz", "usnavajo"): "usden",
                    ("ks", "primary"): "level1",
                    ("ks", "tertiary"): "level3",
                }
                if len(content) == 1:
                    content = aliases.get((key, content[0]), content[0]).split("-")
                content = [] if content in (["true"], ["yes"]) else content
                values.extend([key, *content])
        elif singleton == "t":
            # Optional transformed language followed by alpha/digit field keys.
            offset = next(
                (i for i, part in enumerate(values) if re.fullmatch(r"[a-z][0-9]", part)),
                len(values),
            )
            transformed = values[:offset]
            if transformed:
                parsed = intl_structure("-".join(transformed))
                if parsed is None or any(len(part) == 1 for part in transformed):
                    return None
                transformed = Language.get(parsed).to_tag().lower().split("-")
            fields: dict[str, list[str]] = {}
            while offset < len(values):
                key = values[offset]
                if not re.fullmatch(r"[a-z][0-9]", key) or key in fields:
                    return None
                offset += 1
                start = offset
                while offset < len(values) and len(values[offset]) >= 3:
                    offset += 1
                if offset == start:
                    return None
                fields[key] = values[start:offset]
            values = transformed + [item for key in sorted(fields) for item in [key, *fields[key]]]
        extensions[singleton] = values
    suffix = [item for key in sorted(extensions) for item in [key, *extensions[key]]]
    return "-".join([*base, *suffix, *private])


def normalize_language(value) -> str | None:
    if not isinstance(value, str) or utf16_length(value) > 100:
        return None
    raw = trim(value)
    if not re.fullmatch(r"[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*", raw):
        return None
    structured = intl_structure(raw)
    if structured is None:
        return None
    raw = structured
    try:
        parts = raw.split("-")
        region_index = 2 if len(parts) > 1 and len(parts[1]) == 4 else 1
        region = parts[region_index].upper() if len(parts) > region_index else ""
        if region in {"SU", "810", "172"}:
            successors = {"uk": "UA"}
            if region != "172":
                successors.update(et="EE", lv="LV", lt="LT")
            parts[region_index] = successors.get(parts[0], "RU")
        tag = Language.get("-".join(parts)).to_tag()
        if tag.split("-")[0] in {"other", "und", "zxx", "mul"}:
            return None
        return tag
    except (ValueError, LookupError):
        return None


def supported_language(value) -> str | None:
    tag = normalize_language(value)
    if not tag:
        return None
    match = re.fullmatch(r"([a-z]{2,3})(?:-([A-Z][a-z]{3}))?(?:-[A-Z]{2}|-[0-9]{3})?", tag)
    if not match or match[1] not in SUPPORTED_LANGUAGES:
        return None
    script = "Cyrl" if match[1] in {"ru", "uk", "bg"} else "Grek" if match[1] == "el" else "Latn"
    return tag if not match[2] or match[2] == script else None
