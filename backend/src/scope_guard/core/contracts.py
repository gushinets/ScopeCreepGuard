"""Shared wire conventions; persistence models remain independent of API models."""

import re
from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr
from pydantic.alias_generators import to_camel

Text = Annotated[StrictStr, Field(max_length=100_000)]


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


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    def to_wire(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_unset=True)


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
