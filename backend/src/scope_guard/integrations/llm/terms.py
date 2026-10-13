"""Normalize commercial amount/unit bindings, including localized names and symbols."""

import re
from collections import Counter
from decimal import Decimal
from functools import lru_cache

from babel.numbers import get_currency_name, parse_decimal
from babel.units import format_unit

from scope_guard.domain.change_orders.constants import SUPPORTED_LANGUAGES


@lru_cache(maxsize=1)
def units():
    aliases = {
        "usd": "USD",
        "$": "USD",
        "us$": "USD",
        "eur": "EUR",
        "€": "EUR",
        "rub": "RUB",
        "₽": "RUB",
    }
    for code, names in {
        "USD": "dollar|dollars|dólar|dólares|dolar|dolares|доллар|доллара|долларов",
        "EUR": "euro|euros|евро|євро|ευρώ",
        "RUB": "ruble|rubles|rouble|roubles|рубль|рубля|рублей|rublo|rublos",
    }.items():
        aliases.update(dict.fromkeys(names.split("|"), code))
    for language in SUPPORTED_LANGUAGES:
        for count in (1, 2, 5, Decimal("1.5")):
            for currency in ("USD", "EUR", "RUB"):
                aliases[get_currency_name(currency, count=count, locale=language).casefold()] = (
                    currency
                )
            for length in ("long", "short"):
                rendered = format_unit(count, "duration-hour", length=length, locale=language)
                name = re.sub(r"[\d.,\s\xa0]+", "", rendered).casefold()
                if name:
                    aliases[name] = "hours"
    aliases.update(
        dict.fromkeys(("hour", "hours", "h", "hr", "hrs", "час", "часа", "часов"), "hours")
    )
    alternatives = "|".join(re.escape(name) for name in sorted(aliases, key=len, reverse=True))
    number = r"\d+(?:[.,]\d+)*"
    return aliases, re.compile(
        rf"(?<!\w)(?P<amount>{number})\s*(?P<unit>{alternatives})(?!\w)|"
        rf"(?<!\w)(?P<prefix>{alternatives})\s*(?P<before>{number})(?!\w)",
        re.I,
    )


def mentions(text, language):
    aliases, pattern = units()
    result = Counter()
    for match in pattern.finditer(text):
        unit = aliases[(match["unit"] or match["prefix"]).casefold()]
        number = match["amount"] or match["before"]
        if re.fullmatch(r"\d+\.\d{1,2}", number):
            value = Decimal(number)
        else:
            value = parse_decimal(number, locale=language.split("-")[0])
        result[(unit, value)] += 1
    return result


def preserve_mentions(field, source, translated, source_language, target):
    if mentions(source, source_language) != mentions(translated, target):
        raise ValueError(
            f"{field}.commercial_terms: preserve each amount, unit and currency binding"
        )
