import asyncio
from pathlib import Path
from uuid import uuid4

import pytest


def test_private_test_storage_survives_new_adapter_and_never_overwrites():
    from scope_guard.integrations.storage.filesystem import FilesystemObjectStorage

    root = Path(__file__).parents[3] / "output" / "storage-tests" / uuid4().hex

    async def exercise():
        storage = FilesystemObjectStorage(root)
        await storage.put("exports/example/attempt.pdf", b"saved PDF")
        second = FilesystemObjectStorage(root)
        assert await second.get("exports/example/attempt.pdf") == b"saved PDF"
        with pytest.raises(FileExistsError):
            await second.put("exports/example/attempt.pdf", b"replacement")
        with pytest.raises(ValueError):
            await second.get("../escape")
        assert (await second.list())[0]["key"] == "exports/example/attempt.pdf"

    asyncio.run(exercise())
