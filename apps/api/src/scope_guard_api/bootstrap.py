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


def profile_service(request: Request):
    from scope_guard.database.repositories.profiles import ProfilesUnitOfWork
    from scope_guard.services.profiles.service import ProfileService

    return ProfileService(lambda: ProfilesUnitOfWork(request.app.state.database.new_uow()))


async def current_owner(request: Request) -> dict[str, str]:
    from scope_guard.domain.auth.validation import AuthError
    from scope_guard.integrations.auth.sessions import SESSION_COOKIE_NAME

    owner = await auth_service(request).me(request.cookies.get(SESSION_COOKIE_NAME))
    if owner.get("workspaceAccess") == "email_confirmation_required":
        raise AuthError("errors.emailVerificationRequired", 403)
    return owner


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
            if settings.llm_workflow:
                from scope_guard.database.schema_verification import verify_nonblocking_schema

                if database is None:
                    raise RuntimeError("LLM workflow requires the compatible database schema")
                async with database.engine.begin() as connection:
                    await connection.run_sync(verify_nonblocking_schema)
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


def llm_operations_service(request: Request):
    if not request.app.state.settings.llm_workflow:
        return None
    from scope_guard.database.repositories.llm import LlmSQLStore
    from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
    from scope_guard.integrations.llm.detection import select
    from scope_guard.integrations.llm.policy import policy
    from scope_guard.services.llm.operations import LlmOperations

    state = request.app.state
    return LlmOperations(
        lambda: WorkflowUnitOfWork(state.database.new_uow()),
        LlmSQLStore(state.database.new_uow),
        policy(state.settings),
        state.generation_limiter,
        language_selector=select,
    )


def legacy_llm_result(request, owner, style, value):
    if style == "workflow":
        return value
    if style == "analyze":
        from scope_guard.domain.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
        from scope_guard.domain.analysis.normalization import parse_snapshot
        from scope_guard.integrations.auth.draft_proofs import DraftProofs

        run = value["analysisRun"]
        snapshot = {
            **run["projectSnapshot"],
            "version": 1,
            "documentLanguage": run["requestedDocumentLanguage"],
        }
        proof = DraftProofs(
            request.app.state.settings.auth_secret.get_secret_value(), request.app.state.clock
        ).issue(
            DraftProofClaims(
                DraftProofBinding(
                    str(owner), run["projectId"], run["requestText"], run["interfaceLocale"]
                ),
                parse_snapshot(run["resultSnapshot"], run["interfaceLocale"]),
                freeze(snapshot),
            )
        )
        return {"result": run["resultSnapshot"], "projectSnapshot": snapshot, "proof": proof}
    document = value["draft"]["draftDocument"]
    if style == "reply":
        return {"reply": document["reply"]["text"]}
    if style == "materials":
        order = document["changeOrder"]
        return {
            "materials": {
                "clientLanguage": document["reply"]["language"],
                "replies": document["reply"]["generated"],
                "changeOrder": None
                if order is None
                else {k: order[k] for k in ("description", "timelineImpact", "rationale", "note")},
                **({"changeOrderLabels": order["changeOrderLabels"]} if order else {}),
            }
        }
    result = {
        **value["analysisRun"]["resultSnapshot"],
        "changeOrder": {
            k: document["changeOrder"][k]
            for k in (
                "description",
                "estimatedHours",
                "additionalCost",
                "currency",
                "timelineImpact",
                "rationale",
                "note",
            )
        },
    }
    return {"result": result}


def email_service(request: Request):
    from scope_guard.integrations.email.smtp import SMTPSender
    from scope_guard.services.email.service import EmailService

    return EmailService(SMTPSender(request.app.state.settings))


def confirmation_service(request: Request):
    from scope_guard.database.repositories.email_confirmation import ConfirmationAttempts
    from scope_guard.services.auth.confirmation import ConfirmationService
    from scope_guard.services.auth.tokens import AuthTokenService

    database = request.app.state.database
    return ConfirmationService(
        ConfirmationAttempts(database.new_uow),
        AuthTokenService(lambda: AuthUnitOfWork(database.new_uow()), Passwords()),
        email_service(request),
        request.app.state.settings.public_app_url
        or ("" if request.app.state.settings.production else "http://localhost:3000"),
    )
