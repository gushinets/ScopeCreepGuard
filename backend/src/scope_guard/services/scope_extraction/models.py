from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field

from scope_guard.core.contracts import WireModel


class ExtractionError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


class PagesWithoutText(WireModel):
    code: Literal["pages_without_text"] = "pages_without_text"
    page_numbers: list[int]


class NulRemoved(WireModel):
    code: Literal["nul_removed"] = "nul_removed"


Warning = Annotated[PagesWithoutText | NulRemoved, Field(discriminator="code")]


class ExtractionResponse(WireModel):
    text: str
    warnings: list[Warning]


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    text: str
    warnings: tuple[PagesWithoutText | NulRemoved, ...]
