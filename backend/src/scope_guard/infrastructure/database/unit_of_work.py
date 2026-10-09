"""Transaction ownership only; business repositories are added in ANY-640."""

import asyncio
from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class AsyncUnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback: TracebackType | None) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self._factory = factory
        self._session: AsyncSession | None = None
        self._finished = False

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
        await self.session.commit()
        self._finished = True

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
