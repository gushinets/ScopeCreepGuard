import asyncio
import logging

from sqlalchemy import make_url, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scope_guard.core.config import Settings
from scope_guard.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork


class DatabaseUnavailableError(Exception):
    def __init__(self):
        super().__init__("database_unavailable")


def normalize_url(value: str) -> URL:
    try:
        url = make_url(value)
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError
        if not url.database:
            raise ValueError
        # Libpq target overrides must not bypass explicit URL target selection.
        if set(url.query) - {"sslmode", "sslrootcert", "sslcert", "sslkey"}:
            raise ValueError
        return url.set(drivername="postgresql+psycopg")
    except Exception:
        raise ValueError("unsupported_database_url") from None


class Database:
    def __init__(self, url: URL):
        self.engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_timeout=1,
            connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
            hide_parameters=True,
        )
        self._factory = async_sessionmaker(
            self.engine, expire_on_commit=False, autoflush=False, autobegin=False
        )
        self._probes: set[asyncio.Task] = set()

    def new_uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._factory)

    async def check_connection(self) -> None:
        async def probe():
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))

        def finished(task):
            self._probes.discard(task)
            if not task.cancelled():
                task.exception()

        task = asyncio.create_task(probe())
        self._probes.add(task)
        task.add_done_callback(finished)
        try:
            # Waiting for Psycopg cancellation cleanup can exceed the HTTP deadline.
            # Keep cleanup owned by lifespan while returning readiness on time.
            done, _ = await asyncio.wait({task}, timeout=3)
            if not done:
                task.cancel()
                raise DatabaseUnavailableError()
            task.result()
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Exception:
            raise DatabaseUnavailableError() from None

    async def close(self) -> None:
        for task in self._probes:
            task.cancel()
        if self._probes:
            await asyncio.gather(*self._probes, return_exceptions=True)
        await self.engine.dispose()


def create_database(settings: Settings) -> Database | None:
    if settings.database_url is None:
        return None
    try:
        return Database(normalize_url(settings.database_url.get_secret_value()))
    except ValueError:
        logging.getLogger("scope_guard").error("database_configuration_invalid")
        return None


def event_loop() -> asyncio.AbstractEventLoop:
    """Explicit Uvicorn loop factory, including Psycopg-compatible Windows startup."""
    return asyncio.SelectorEventLoop()
