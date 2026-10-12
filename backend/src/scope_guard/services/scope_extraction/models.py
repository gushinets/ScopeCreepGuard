from dataclasses import dataclass
from typing import Literal


class ExtractionError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PagesWithoutText:
    page_numbers: tuple[int, ...]
    code: Literal["pages_without_text"] = "pages_without_text"

    def __post_init__(self):
        object.__setattr__(self, "page_numbers", tuple(self.page_numbers))


@dataclass(frozen=True, slots=True)
class NulRemoved:
    code: Literal["nul_removed"] = "nul_removed"


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    text: str
    warnings: tuple[PagesWithoutText | NulRemoved, ...]

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "warnings": [
                {"code": warning.code, "pageNumbers": list(warning.page_numbers)}
                if isinstance(warning, PagesWithoutText)
                else {"code": warning.code}
                for warning in self.warnings
            ],
        }
