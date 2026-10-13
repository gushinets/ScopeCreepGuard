"""Persistent test adapter. Never selected as production storage."""

import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path


class FilesystemObjectStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"exports/[a-zA-Z0-9/_-]+\.pdf", key):
            raise ValueError("invalid_object_key")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("invalid_object_key")
        return path

    async def put(self, key: str, data: bytes) -> None:
        def write():
            path = self.path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(data)
                output.flush()

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self.path(key).read_bytes)

    async def list(self) -> list[dict]:
        return await asyncio.to_thread(
            lambda: [
                {
                    "key": path.relative_to(self.root).as_posix(),
                    "createdAt": datetime.fromtimestamp(path.stat().st_mtime, UTC),
                }
                for path in self.root.rglob("*.pdf")
            ]
        )

    async def remove(self, key: str) -> None:
        await asyncio.to_thread(self.path(key).unlink, missing_ok=True)
