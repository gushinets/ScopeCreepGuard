import base64
import json

from scope_guard.services.documents.ports import IsolatedOperations


class ExtractionService:
    def __init__(self, operations: IsolatedOperations):
        self.operations = operations

    async def extract(self, name: str, mime: str, data: bytes) -> bytes:
        payload = json.dumps(
            {"name": name, "mime": mime, "data": base64.b64encode(data).decode("ascii")}
        ).encode()
        return await self.operations.run("extract", payload)
