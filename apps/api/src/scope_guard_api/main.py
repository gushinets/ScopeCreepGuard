import time
from collections.abc import Callable

from fastapi import FastAPI
from scope_guard.core.config import Settings
from scope_guard.domain.analysis.domain import GenerationError
from scope_guard.services.auth.use_cases import AuthError
from scope_guard.services.evaluations.use_cases import EvaluationError
from scope_guard.services.projects.use_cases import ProjectError

from scope_guard_api.activity_context import ActivityContextMiddleware
from scope_guard_api.bootstrap import configure_app, lifespan
from scope_guard_api.contracts import ErrorResponse
from scope_guard_api.draft_cache import DraftReadCacheMiddleware
from scope_guard_api.errors import (
    ErrorCode,
    UnhandledErrorMiddleware,
    install_error_handlers,
    json_error,
)
from scope_guard_api.origin import OriginMiddleware
from scope_guard_api.routes.auth import router as auth_router
from scope_guard_api.routes.drafts import router as drafts_router
from scope_guard_api.routes.evaluations import router as evaluations_router
from scope_guard_api.routes.generation import router as generation_router
from scope_guard_api.routes.health import router as health_router
from scope_guard_api.routes.locale import router as locale_router
from scope_guard_api.routes.password_recovery import router as recovery_router
from scope_guard_api.routes.profiles import router as profiles_router
from scope_guard_api.routes.projects import router as projects_router
from scope_guard_api.routes.technical import router as technical_router
from scope_guard_api.routes.workflow import router as workflow_router
from scope_guard_api.workflow_boundary import WorkflowBoundary


def create_app(settings: Settings | None = None, clock: Callable[[], float] = time.time) -> FastAPI:
    settings = settings if settings is not None else Settings()

    application = FastAPI(
        title="Scope Creep Guard API",
        version="0.1.0",
        lifespan=lifespan(settings),
        responses={500: {"model": ErrorResponse, "description": "Unexpected request failure"}},
    )
    application.state.settings = settings
    application.state.clock = clock
    configure_app(application, settings)
    install_error_handlers(application)
    application.add_middleware(UnhandledErrorMiddleware)
    application.add_middleware(OriginMiddleware, allowed_origins=settings.allowed_origins)
    application.add_middleware(DraftReadCacheMiddleware)
    application.add_middleware(ActivityContextMiddleware)
    if settings.llm_workflow and not settings.workflow_v2:
        raise ValueError("LLM workflow requires persistent workflow activation")
    application.add_middleware(
        WorkflowBoundary, enabled=settings.workflow_v2, llm_enabled=settings.llm_workflow
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(recovery_router)
    application.include_router(projects_router)
    application.include_router(generation_router)
    application.include_router(technical_router)
    application.include_router(drafts_router)
    application.include_router(locale_router)
    application.include_router(evaluations_router)
    application.include_router(workflow_router)
    application.include_router(profiles_router)

    from scope_guard.domain.drafts.workflow import WorkflowError
    from starlette.responses import JSONResponse

    @application.exception_handler(WorkflowError)
    async def workflow_error(_request, error: WorkflowError):
        return JSONResponse(
            {"error": error.code, **({"fields": error.fields} if error.fields else {})},
            error.status,
            headers={"Cache-Control": "private, no-store"},
        )

    @application.exception_handler(GenerationError)
    async def generation_error(_request, error: GenerationError):
        return JSONResponse(
            {"error": error.code}, error.status, headers={"Cache-Control": "private, no-store"}
        )

    @application.exception_handler(AuthError)
    async def auth_error(_request, error: AuthError):
        return json_error(ErrorCode(error.code), error.status)

    @application.exception_handler(ProjectError)
    async def project_error(_request, error: ProjectError):
        return json_error(ErrorCode(error.code), error.status)

    @application.exception_handler(EvaluationError)
    async def evaluation_error(_request, error: EvaluationError):
        return json_error(ErrorCode(error.code), error.status)

    return application


app = create_app()
