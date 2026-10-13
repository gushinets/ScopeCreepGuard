import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from scope_guard.core.logging import configure_logging
from scope_guard.database.queries.drafts import DraftReadWork
from scope_guard.database.queries.evaluations import EvaluationReadWork
from scope_guard.database.queries.projects import ProjectReadWork
from scope_guard.database.repositories.projects import ProjectUnitOfWork
from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.database.session import create_database
from scope_guard.integrations.auth.passwords import Passwords
from scope_guard.integrations.auth.sessions import Sessions
from scope_guard.integrations.documents.technical.operations import TechnicalOperations
from scope_guard.integrations.llm.openai import OpenAIGeneration
from scope_guard.integrations.llm.rate_limit import GenerationLimiter
from scope_guard.services.auth.use_cases import AuthService
from scope_guard.services.projects.use_cases import ProjectService


def auth_service(request: Request) -> AuthService:
    database = getattr(request.app.state, "database", None)
    settings = request.app.state.settings
    secret = settings.auth_secret.get_secret_value() if settings.auth_secret else ""
    sessions = Sessions(secret, request.app.state.clock) if secret else None
    return AuthService(
        (lambda: AuthUnitOfWork(database.new_uow())) if database else None,
        Passwords(),
        sessions,
    )


async def current_owner(request: Request) -> dict[str, str]:
    from scope_guard.integrations.auth.sessions import SESSION_COOKIE_NAME

    return await auth_service(request).me(request.cookies.get(SESSION_COOKIE_NAME))


def project_service(request: Request) -> ProjectService:
    return ProjectService(
        lambda: ProjectUnitOfWork(request.app.state.database.new_uow()),
        reads=lambda: ProjectReadWork(request.app.state.database.new_uow()),
    )


def draft_service(request: Request):
    from scope_guard.database.repositories.draft_persistence import DraftUnitOfWork
    from scope_guard.services.drafts.use_cases import DraftService

    return DraftService(
        lambda: DraftUnitOfWork(request.app.state.database.new_uow()),
        request.app.state.clock,
        reads=lambda: DraftReadWork(request.app.state.database.new_uow()),
    )


def evaluation_service(request: Request):
    from scope_guard.database.repositories.evaluations import EvaluationUnitOfWork
    from scope_guard.services.evaluations.use_cases import EvaluationService

    return EvaluationService(
        lambda: EvaluationUnitOfWork(request.app.state.database.new_uow()),
        reads=lambda: EvaluationReadWork(request.app.state.database.new_uow()),
    )


def generation_service(request: Request):
    from scope_guard.database.queries.generation import GenerationReadWork
    from scope_guard.integrations.auth.draft_proofs import DraftProofs
    from scope_guard.services.analysis.use_cases import GenerationUseCases

    state = request.app.state
    secret = state.settings.auth_secret.get_secret_value() if state.settings.auth_secret else ""
    return GenerationUseCases(
        lambda: GenerationReadWork(state.database.new_uow()),
        state.generator,
        DraftProofs(secret, state.clock),
        state.generation_limiter,
        state.clock,
    )


def document_use_cases(request: Request):
    from scope_guard.database.repositories.draft_persistence import DraftUnitOfWork
    from scope_guard.services.documents.use_cases import DocumentUseCases

    database = request.app.state.database
    return DocumentUseCases(
        lambda: DraftUnitOfWork(database.new_uow()),
        lambda: ProjectUnitOfWork(database.new_uow()),
    )


def lifespan(settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logging.getLogger("scope_guard").info("Backend started")
        database = create_database(settings)
        app.state.database = database
        try:
            yield
        finally:
            await app.state.generator.close()
            if database is not None:
                await database.close()

    return lifespan


def configure_app(application, settings):
    application.state.export_storage = object_storage(settings)
    application.state.generator = OpenAIGeneration(
        settings.openai_api_key.get_secret_value() if settings.openai_api_key else "",
        model=settings.openai_model,
    )
    application.state.generation_limiter = GenerationLimiter()
    application.state.technical_operations = TechnicalOperations()
    for name in ("openai", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def document_renderer(request: Request):
    from scope_guard.services.documents.rendering import DocumentRendering

    return DocumentRendering(request.app.state.technical_operations)


def extraction_service(request: Request):
    from scope_guard.services.scope_extraction.use_cases import ExtractionService

    return ExtractionService(request.app.state.technical_operations)


def health_service(request: Request):
    from scope_guard.services.health.service import HealthService

    return HealthService(getattr(request.app.state, "database", None))


def draft_proof_service(request: Request):
    from scope_guard.integrations.auth.draft_proofs import DraftProofs
    from scope_guard.services.drafts.proofs import DraftProofService

    state = request.app.state
    secret = state.settings.auth_secret.get_secret_value() if state.settings.auth_secret else ""
    return DraftProofService(lambda: DraftProofs(secret, state.clock))


def object_storage(settings):
    if not settings.export_bucket:
        return None
    from scope_guard.integrations.storage.s3 import S3ObjectStorage

    return S3ObjectStorage(
        settings.export_bucket,
        endpoint=settings.export_endpoint or None,
        region=settings.export_region,
        access_key=settings.export_access_key.get_secret_value()
        if settings.export_access_key
        else None,
        secret_key=settings.export_secret_key.get_secret_value()
        if settings.export_secret_key
        else None,
    )


def workflow_service(request: Request):
    from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
    from scope_guard.services.drafts.workflow import WorkflowService

    state = request.app.state
    return WorkflowService(
        lambda: WorkflowUnitOfWork(state.database.new_uow()),
        state.generator,
        state.generation_limiter,
        state.export_storage,
    )
