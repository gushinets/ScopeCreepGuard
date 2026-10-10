import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from scope_guard.api.contracts import ErrorResponse
from scope_guard.api.errors import (
    ErrorCode,
    UnhandledErrorMiddleware,
    install_error_handlers,
    json_error,
)
from scope_guard.api.origin import OriginMiddleware
from scope_guard.api.routes.auth import router as auth_router
from scope_guard.api.routes.generation import router as generation_router
from scope_guard.api.routes.health import router as health_router
from scope_guard.api.routes.projects import router as projects_router
from scope_guard.core.config import Settings
from scope_guard.core.logging import configure_logging
from scope_guard.infrastructure.database.session import create_database
from scope_guard.infrastructure.llm.openai import OpenAIGeneration
from scope_guard.infrastructure.llm.rate_limit import GenerationLimiter
from scope_guard.modules.auth.use_cases import AuthError
from scope_guard.modules.projects.use_cases import ProjectError


def create_app(settings: Settings | None = None, clock: Callable[[], float] = time.time) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logging.getLogger("scope_guard").info("Backend started")
        database = create_database(settings)
        app.state.database = database
        try:
            yield
        finally:
            await application.state.generator.close()
            if database is not None:
                await database.close()

    application = FastAPI(
        title="Scope Creep Guard API",
        version="0.1.0",
        lifespan=lifespan,
        responses={500: {"model": ErrorResponse, "description": "Unexpected request failure"}},
    )
    application.state.settings = settings
    application.state.clock = clock
    application.state.generator = OpenAIGeneration(
        settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    )
    application.state.generation_limiter = GenerationLimiter()
    for name in ("openai", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    install_error_handlers(application)
    application.add_middleware(UnhandledErrorMiddleware)
    application.add_middleware(OriginMiddleware, allowed_origins=settings.allowed_origins)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(projects_router)
    application.include_router(generation_router)

    @application.exception_handler(AuthError)
    async def auth_error(_request, error: AuthError):
        return json_error(ErrorCode(error.code), error.status)

    @application.exception_handler(ProjectError)
    async def project_error(_request, error: ProjectError):
        return json_error(ErrorCode(error.code), error.status)

    return application


app = create_app()
