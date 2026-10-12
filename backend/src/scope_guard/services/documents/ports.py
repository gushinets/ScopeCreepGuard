from typing import Protocol

from scope_guard.domain.analysis.domain import ABSENT, Labels


class DocumentLocalization(Protocol):
    def supported_language(self, value: str) -> str: ...
    def document_date(self, value: str, language: str) -> str: ...
    def document_labels(
        self, language: str, supplied: Labels | object = ABSENT
    ) -> dict[str, str]: ...


class IsolatedOperations(Protocol):
    async def run(self, mode: str, data: bytes) -> bytes: ...


class TechnicalError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)
