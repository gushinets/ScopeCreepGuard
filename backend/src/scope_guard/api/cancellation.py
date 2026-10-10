"""Watch disconnect only after body consumption; cancel and await all work."""

import asyncio
from contextlib import suppress


async def run_connected(request, operation):
    task = asyncio.create_task(operation)

    async def watch():
        while True:
            if (await request.receive())["type"] == "http.disconnect":
                task.cancel()
                return

    watcher = asyncio.create_task(watch())
    try:
        return await task
    finally:
        watcher.cancel()
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            await watcher
        with suppress(asyncio.CancelledError):
            await task
