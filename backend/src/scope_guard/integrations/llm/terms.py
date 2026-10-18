"""Normalize commercial amount/unit bindings, including localized names and symbols."""

import re
from collections import Counter
from decimal import Decimal
from functools import lru_cache

from babel.numbers import get_currency_name, parse_decimal
from babel.units import format_unit

from scope_guard.domain.change_orders.constants import SUPPORTED_LANGUAGES

NUMBER_WORDS = {
    "en": (
        "zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty"
    ).split(),
    "es": (
        "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece "
        "catorce quince dieciséis diecisiete dieciocho diecinueve veinte"
    ).split(),
    "ru": (
        "ноль один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать "
        "тринадцать четырнадцать пятнадцать шестнадцать семнадцать восемнадцать "
        "девятнадцать двадцать"
    ).split(),
}


def normalize_number_words(text, language):
    base = language.split("-")[0]
    words = dict(zip(NUMBER_WORDS.get(base, []), range(21), strict=False))
    words.update(
        {"a": 1, "an": 1}
        if base == "en"
        else {"un": 1, "una": 1}
        if base == "es"
        else {"одна": 1, "одно": 1, "две": 2}
        if base == "ru"
        else {}
    )
    for start, tens in (
        ((20, "twenty thirty forty fifty sixty seventy eighty ninety"),)
        if base == "en"
        else (
            ((20, "veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa"),)
            if base == "es"
            else (
                (
                    20,
                    "двадцать тридцать сорок пятьдесят шестьдесят семьдесят восемьдесят девяносто",
                ),
            )
            if base == "ru"
            else ()
        )
    ):
        words.update({word: start + i * 10 for i, word in enumerate(tens.split())})
    if base == "es":
        words.update(
            {
                "cien": 100,
                "ciento": 100,
                "veintiuno": 21,
                "veintiuna": 21,
                "veintidós": 22,
                "veintitrés": 23,
                "veinticuatro": 24,
                "veinticinco": 25,
                "veintiséis": 26,
                "veintisiete": 27,
                "veintiocho": 28,
                "veintinueve": 29,
            }
        )
    elif base == "ru":
        words.update(
            dict(
                zip(
                    (
                        "сто двести триста четыреста пятьсот шестьсот семьсот восемьсот девятьсот"
                    ).split(),
                    range(100, 1000, 100),
                    strict=True,
                )
            )
        )
    # Consume a complete recognized phrase. Never interpret the final word of an
    # unsupported compound as its complete quantity ("twenty five" is 25, not 5).
    scale = {
        "en": {"hundred": 100, "thousand": 1000},
        "es": {"mil": 1000},
        "ru": {"тысяча": 1000, "тысячи": 1000, "тысяч": 1000},
    }.get(base, {})
    connectors = {"en": {"and"}, "es": {"y"}}.get(base, set())
    tokens = sorted(set(words) | set(scale), key=len, reverse=True)
    if not tokens:
        return text
    atom = "(?:" + "|".join(re.escape(w) for w in tokens) + ")"
    connector = "(?:" + "|".join(connectors) + ")" if connectors else r"(?!)"
    pattern = re.compile(
        r"\b" + atom + r"(?:[ -]+(?:" + connector + r"[ -]+)?" + atom + r")*\b", re.I
    )

    def convert(match):
        total, current = 0, 0
        for word in re.findall(r"\w+", match[0].casefold()):
            if word in connectors:
                continue
            if word in scale:
                if scale[word] == 100:
                    current = max(1, current) * 100
                else:
                    total += max(1, current) * scale[word]
                    current = 0
            else:
                current += words[word]
        return str(total + current)

    return pattern.sub(convert, text)


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
    number = r"\d+(?:[.,]\d+)*(?:[ \xa0\u202f]\d{3})*(?:[.,]\d+)?"
    return aliases, re.compile(
        rf"(?<!\w)(?P<amount>{number})\s*(?P<unit>{alternatives})(?!\w)|"
        rf"(?<!\w)(?P<prefix>{alternatives})\s*(?P<before>{number})(?!\w)",
        re.I,
    )


def mentions(text, language):
    aliases, pattern = units()
    result = Counter()
    for match in pattern.finditer(normalize_number_words(text, language)):
        unit = aliases[(match["unit"] or match["prefix"]).casefold()]
        number = match["amount"] or match["before"]
        if re.fullmatch(r"\d+\.\d{1,2}", number):
            value = Decimal(number)
        else:
            value = parse_decimal(
                re.sub(r"[ \xa0\u202f]", "", number), locale=language.replace("-", "_")
            )
        result[(unit, value)] += 1
    return result


def preserve_mentions(field, source, translated, source_language, target, *, money=True):
    original, observed = mentions(source, source_language), mentions(translated, target)
    if not money:
        original = Counter({pair: count for pair, count in original.items() if pair[0] == "hours"})
        observed = Counter({pair: count for pair, count in observed.items() if pair[0] == "hours"})
    if original != observed:
        raise ValueError(
            f"{field}.commercial_terms: preserve each amount, unit and currency binding"
        )
