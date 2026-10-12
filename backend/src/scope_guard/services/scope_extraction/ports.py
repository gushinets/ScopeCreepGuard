from typing import Protocol

from scope_guard.services.scope_extraction.models import PagesWithoutText


class ScopeReaders(Protocol):
    def read_pdf(self, data: bytes) -> tuple[str, tuple[PagesWithoutText, ...]]: ...
    def read_text(self, data: bytes) -> str: ...
