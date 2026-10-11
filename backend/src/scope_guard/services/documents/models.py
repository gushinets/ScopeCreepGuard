from dataclasses import dataclass

from scope_guard.modules.drafts.values import JsonObject, JsonValue


class DocumentError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Row:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class DocumentSource:
    editor: JsonObject
    project_snapshot: JsonValue


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    labels: tuple[tuple[str, str], ...]
    reference: str
    created_date: str
    metadata: tuple[Row, ...]
    description: str
    commercial: tuple[Row, ...]
    schedule: str
    additional: tuple[Row, ...]
    approval: tuple[Row, ...]
    project_snapshot: JsonValue = None

    def label(self, key: str) -> str:
        return dict(self.labels)[key]
