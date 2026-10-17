import asyncio
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

"""Transaction ownership only; business repositories are added in ANY-640."""


class AsyncUnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback: TracebackType | None) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        after_commit: Callable[[], Awaitable[None]] | None = None,
    ):
        self._factory = factory
        self._session: AsyncSession | None = None
        self._finished = False
        self._after_commit = after_commit

    async def __aenter__(self) -> Self:
        if self._session is not None or self._finished:
            raise RuntimeError("uow_finished")
        self._session = self._factory()
        await self._session.begin()
        return self

    @property
    def session(self) -> AsyncSession:
        if self._session is None or self._finished:
            raise RuntimeError("uow_finished")
        return self._session

    async def commit(self) -> None:
        session = self.session
        dirty = session.info.get("marketing_metrics_dirty", False)
        await session.commit()
        self._finished = True
        if dirty and self._after_commit is not None:
            # T1 is committed and its connection released before T2 opens a new UoW.
            # Closing also prevents accidental reuse while the callback executes.
            try:
                await session.close()
                await self._after_commit()
            except Exception:
                logging.getLogger("scope_guard").exception(
                    "marketing_metrics_reconciliation_failed"
                )

    async def rollback(self) -> None:
        await self.session.rollback()
        self._finished = True

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        async def cleanup():
            try:
                if not self._finished and self._session is not None:
                    await self._session.rollback()
            finally:
                self._finished = True
                if self._session is not None:
                    await self._session.close()

        task = asyncio.create_task(cleanup())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise
