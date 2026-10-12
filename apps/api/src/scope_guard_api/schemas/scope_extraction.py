from typing import Annotated, Literal

from pydantic import Field

from scope_guard_api.schemas.shared import WireModel


class PagesWithoutText(WireModel):
    code: Literal["pages_without_text"] = "pages_without_text"
    page_numbers: list[int]


class NulRemoved(WireModel):
    code: Literal["nul_removed"] = "nul_removed"


Warning = Annotated[PagesWithoutText | NulRemoved, Field(discriminator="code")]


class ExtractionResponse(WireModel):
    text: str
    warnings: list[Warning]
