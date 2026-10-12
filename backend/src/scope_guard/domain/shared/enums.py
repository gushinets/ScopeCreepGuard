from enum import StrEnum


class Industry(StrEnum):
    Development = "Development"
    Design = "Design"
    Marketing = "Marketing"


class Verdict(StrEnum):
    in_scope = "in_scope"
    borderline = "borderline"
    out_of_scope = "out_of_scope"


class PricingModel(StrEnum):
    hourly = "hourly"
    fixed = "fixed"


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class EvaluationAccuracy(StrEnum):
    correct = "correct"
    wrong = "wrong"
    debatable = "debatable"
