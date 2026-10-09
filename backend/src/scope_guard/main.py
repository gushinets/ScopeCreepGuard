import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from scope_guard.api.routes.health import router as health_router
from scope_guard.core.config import Settings
from scope_guard.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logging.getLogger("scope_guard").info("Backend started")
        yield

    application = FastAPI(title="Scope Creep Guard API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.include_router(health_router)
    return application


app = create_app()
