from fastapi import Request

from scope_guard.database.repositories.projects import ProjectUnitOfWork
from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.integrations.auth.passwords import Passwords
from scope_guard.integrations.auth.sessions import Sessions
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
    return ProjectService(lambda: ProjectUnitOfWork(request.app.state.database.new_uow()))


def draft_service(request: Request):
    from scope_guard.database.repositories.draft_persistence import DraftUnitOfWork
    from scope_guard.services.drafts.use_cases import DraftService

    return DraftService(
        lambda: DraftUnitOfWork(request.app.state.database.new_uow()), request.app.state.clock
    )


def evaluation_service(request: Request):
    from scope_guard.database.repositories.evaluations import EvaluationUnitOfWork
    from scope_guard.services.evaluations.use_cases import EvaluationService

    return EvaluationService(lambda: EvaluationUnitOfWork(request.app.state.database.new_uow()))


def generation_service(request: Request):
    from scope_guard.database.repositories.generation import GenerationReadWork
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
