from fastapi import Request

from scope_guard.infrastructure.auth.passwords import Passwords
from scope_guard.infrastructure.auth.sessions import Sessions
from scope_guard.infrastructure.database.repositories.users import AuthUnitOfWork
from scope_guard.modules.auth.use_cases import AuthService


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
