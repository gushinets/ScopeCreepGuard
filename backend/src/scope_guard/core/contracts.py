"""Shared wire conventions; persistence models remain independent of API models."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr
from pydantic.alias_generators import to_camel

from scope_guard.domain.shared.enums import (  # noqa: F401
    Currency,
    EvaluationAccuracy,
    Industry,
    PricingModel,
    Verdict,
)
from scope_guard.domain.shared.validation import iso_date, language_tag  # noqa: F401

Text = Annotated[StrictStr, Field(max_length=100_000)]


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    def to_wire(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_unset=True)
