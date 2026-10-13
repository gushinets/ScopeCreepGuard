"""HTTP compatibility only; neither admission nor polling executes an operation."""

from uuid import UUID

from fastapi.encoders import jsonable_encoder
from scope_guard.domain.drafts.workflow import WorkflowError
from starlette.responses import JSONResponse

from scope_guard_api.dependencies import legacy_llm_result, llm_operations_service


def command_key(request, body):
    header, supplied = request.headers.get("Idempotency-Key"), body.get("operationId")
    if header and supplied and header != str(supplied):
        raise WorkflowError("operationMismatch", 400)
    try:
        return str(UUID(header or str(supplied)))
    except (ValueError, TypeError):
        raise WorkflowError("operationRequired", 428) from None


def status_payload(request, owner, status):
    if status["result"] is not None:
        status = {
            **status,
            "result": legacy_llm_result(request, owner, status["responseFormat"], status["result"]),
        }
    return status


async def admit_response(request, owner, identifier, kind, body):
    service = llm_operations_service(request)
    if service is None:
        return None
    body = {**body, "operationId": command_key(request, body)}
    pending = await service.admit(owner, identifier, kind, body)
    status = status_payload(
        request, owner, await service.status(owner, UUID(pending["operationId"]))
    )
    headers = {
        "Cache-Control": "private, no-store",
        "Idempotency-Key": body["operationId"],
        "Location": pending["statusUrl"],
        "Retry-After": "2",
    }
    if status["status"] == "succeeded":
        return JSONResponse(jsonable_encoder(status["result"]), headers=headers)
    if status["status"] == "failed":
        return JSONResponse(
            {"error": status["error"]["code"], "operationId": pending["operationId"]},
            status["error"]["status"],
            headers=headers,
        )
    return JSONResponse(jsonable_encoder(pending), 202, headers=headers)
