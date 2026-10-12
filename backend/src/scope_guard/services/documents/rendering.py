import json

from scope_guard.domain.drafts.validation import parse_editor
from scope_guard.domain.drafts.values import thaw_json
from scope_guard.services.documents.models import DocumentError, DocumentSource
from scope_guard.services.documents.ports import IsolatedOperations


class DocumentRendering:
    def __init__(self, operations: IsolatedOperations):
        self.operations = operations

    async def render(self, source: DocumentSource) -> bytes:
        editor = thaw_json(source.editor)
        try:
            parse_editor(editor)
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise DocumentError("pdfDocumentInvalid") from None
        payload = json.dumps(
            {"changeOrder": editor, "projectSnapshot": thaw_json(source.project_snapshot)},
            ensure_ascii=False,
        ).encode()
        return await self.operations.run("pdf", payload)
