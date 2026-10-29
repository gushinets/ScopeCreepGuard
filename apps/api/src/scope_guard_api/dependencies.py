from fastapi import Request

from scope_guard_api import bootstrap


def auth_service(request: Request):
    return bootstrap.auth_service(request)


def profile_service(request: Request):
    return bootstrap.profile_service(request)


async def current_owner(request: Request) -> dict[str, str]:
    return await auth_service(request).me(request.cookies.get("scg_session"))


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
