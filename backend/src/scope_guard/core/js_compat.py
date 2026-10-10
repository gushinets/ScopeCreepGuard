"""Small ECMAScript compatibility surface required by existing generation contracts."""

import json
import math
import re

JS_SPACE = "\x09\x0a\x0b\x0c\x0d\x20\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"  # noqa: E501 - frozen compatibility literal


def trim(value: str) -> str:
    return value.strip(JS_SPACE)


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le", errors="surrogatepass")) // 2


def number_string(value: int | float) -> str:
    try:
        number = float(value)
    except OverflowError:
        return "null"
    if not math.isfinite(number):
        return "null"
    if number == 0:
        return "0"
    raw = repr(number).lower()
    if 1e-6 <= abs(number) < 1e21:
        from decimal import Decimal

        return (
            format(Decimal(raw), "f").rstrip("0").rstrip(".")
            if "." in format(Decimal(raw), "f")
            else format(Decimal(raw), "f")
        )
    mantissa, exponent = raw.split("e") if "e" in raw else (raw, "0")
    exponent_int = int(exponent)
    return (
        mantissa.removesuffix(".0")
        + "e"
        + ("+" if exponent_int >= 0 else "-")
        + str(abs(exponent_int))
    )


def stringify(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return number_string(value)
    if isinstance(value, str):
        # JSON.stringify escapes lone surrogate code points, not valid Unicode.
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return re.sub(r"[\ud800-\udfff]", lambda m: f"\\u{ord(m[0]):04x}", raw)
    if isinstance(value, (tuple, list)):
        return "[" + ",".join(stringify(item) for item in value) + "]"
    keys = list(value)
    indexes = sorted(
        (key for key in keys if re.fullmatch(r"0|[1-9][0-9]*", key) and int(key) < 4294967295),
        key=int,
    )
    keys = indexes + [key for key in keys if key not in indexes]
    return "{" + ",".join(stringify(key) + ":" + stringify(value[key]) for key in keys) + "}"


def js_string(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int, float)):
        return stringify(value)
    if isinstance(value, list):
        return ",".join("" if item is None else js_string(item) for item in value)
    return "[object Object]"


def date_parse_finite(value: object) -> bool:
    """ISO and legacy persisted-date forms accepted by the existing V8 parser."""
    if not isinstance(value, str) or not trim(value):
        return False
    raw = trim(value)
    pattern = (
        r"([+-][0-9]{6}|[0-9]{4})(?:-([0-9]{1,2})(?:-([0-9]{1,2}))?)?"
        r"(?:T([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]+))?)?"
        r"(Z|[+-][0-9]{2}:?[0-9]{2})?)?"
    )
    match = re.fullmatch(pattern, raw)
    if match:
        year = int(match[1])
        month, day = int(match[2] or 1), int(match[3] or 1)
        hour, minute, second = (int(match[index] or 0) for index in (4, 5, 6))
        fraction = float("0." + (match[7] or "0"))
        if not (
            1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 24 and minute < 60 and second < 60
        ):
            return False
        if hour == 24 and (minute or second or fraction):
            return False
        if match[4] and (not match[2] or not match[3] or len(match[2]) != 2 or len(match[3]) != 2):
            return False
        zone = match[8]
        offset = 0
        if zone and zone != "Z":
            digits = zone[1:].replace(":", "")
            if int(digits[:2]) > 23 or int(digits[2:]) > 59:
                return False
            offset = (int(digits[:2]) * 60 + int(digits[2:])) * (1 if zone[0] == "+" else -1)
        # Proleptic Gregorian days with overflow, including year zero and expanded years.
        adjusted = year - (month <= 2)
        era = adjusted // 400
        yoe = adjusted - era * 400
        month_index = month + (-3 if month > 2 else 9)
        days = (
            era * 146097
            + yoe * 365
            + yoe // 4
            - yoe // 100
            + (153 * month_index + 2) // 5
            + day
            - 1
            - 719468
        )
        milliseconds = (
            days * 86400 + hour * 3600 + minute * 60 + second + fraction - offset * 60
        ) * 1000
        return abs(milliseconds) <= 8_640_000_000_000_000
    if re.fullmatch(r"[0-9]{1,2}", raw):
        number = int(raw)
        return number <= 12 or number >= 32
    from datetime import datetime
    from email.utils import parsedate_to_datetime

    try:
        parsedate_to_datetime(raw)
        return True
    except (ValueError, TypeError, OverflowError):
        pass
    for pattern in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            datetime.strptime(raw, pattern)
            return True
        except ValueError:
            pass
    return False
