from fastapi import Request

from scope_guard_api import bootstrap


def auth_service(request: Request):
    return bootstrap.auth_service(request)


def recovery_service(request: Request):
    from scope_guard.database.repositories.password_recovery import RecoveryQueue
    from scope_guard.domain.auth.recovery import RecoveryUnavailable

    database = getattr(request.app.state, "database", None)
    secret = request.app.state.settings.auth_secret
    if database is None or secret is None:
        raise RecoveryUnavailable()
    return RecoveryBoundary(
        RecoveryQueue(database.new_uow, secret.get_secret_value()),
        bootstrap.confirmation_service(request).tokens,
    )


class RecoveryBoundary:
    """Translate infrastructure errors at composition, without leaking provider detail."""

    def __init__(self, queue, tokens):
        self.queue, self.tokens = queue, tokens

    async def _call(self, operation, *args):
        from scope_guard.domain.auth.recovery import RecoveryUnavailable
        from sqlalchemy.exc import SQLAlchemyError

        try:
            return await operation(*args)
        except (SQLAlchemyError, TimeoutError):
            raise RecoveryUnavailable() from None

    async def request(self, *args):
        return await self._call(self.queue.request, *args)

    async def reset_limit(self, source):
        return await self._call(self.queue.reset_limit, source)

    async def reset_password(self, *args):
        return await self._call(self.tokens.reset_password, *args)


def profile_service(request: Request):
    return bootstrap.profile_service(request)


async def current_owner(request: Request) -> dict[str, str]:
    return await bootstrap.current_owner(request)


def project_service(request: Request):
    return bootstrap.project_service(request)


def draft_service(request: Request):
    return bootstrap.draft_service(request)


def evaluation_service(request: Request):
    return bootstrap.evaluation_service(request)


def generation_service(request: Request):
    return bootstrap.generation_service(request)


def document_use_cases(request: Request):
    return bootstrap.document_use_cases(request)


def document_renderer(request: Request):
    return bootstrap.document_renderer(request)


def extraction_service(request: Request):
    return bootstrap.extraction_service(request)


def health_service(request: Request):
    return bootstrap.health_service(request)


def draft_proof_service(request: Request):
    return bootstrap.draft_proof_service(request)


def workflow_service(request: Request):
    return bootstrap.workflow_service(request)


def llm_operations_service(request: Request):
    return bootstrap.llm_operations_service(request)


def legacy_llm_result(request, owner, style, value):
    return bootstrap.legacy_llm_result(request, owner, style, value)


def email_service(request: Request):
    return bootstrap.email_service(request)
