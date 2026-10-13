from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from scope_guard.core.telemetry import correlation_id, log_event
from scope_guard.domain.analysis.domain import GenerationError
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.shared.js_compat import stringify
from scope_guard.services.change_orders.use_cases import EstimateChangeOrder
from starlette.responses import JSONResponse

from scope_guard_api.cancellation import run_connected
from scope_guard_api.contracts import (
    AnalyzeResponse,
    ErrorResponse,
    EstimateResponse,
    MaterialsResponse,
    ReplyResponse,
)
from scope_guard_api.dependencies import current_owner, generation_service
from scope_guard_api.errors import ApiError, read_json_object
from scope_guard_api.generation_input import (
    parse_analyze,
    parse_estimate,
    parse_materials,
    parse_reply,
)
from scope_guard_api.generation_output import analysis_to_wire, materials_to_wire, snapshot_to_wire
from scope_guard_api.llm_response import admit_response, command_key
from scope_guard_api.locale import resolve_locale
from scope_guard_api.schemas.workflow import PendingLlmOperation

router = APIRouter(
    tags=["generation"],
    responses={
        code: {"model": ErrorResponse}
        for code in (400, 401, 403, 404, 409, 426, 428, 429, 502, 503)
    },
)
Owner = Annotated[dict[str, str], Depends(current_owner)]


class GenerationJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return stringify(content).encode("utf-8")


def request_contract(required, properties):
    return {
        "description": "With the LLM workflow enabled, requires an owned working draftId, "
        "expectedRevision, "
        "and a stable UUID operationId or Idempotency-Key. Returns 202 for pending work; poll "
        "statusUrl until terminal. Client snapshots are not authoritative.",
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": False,
                "schema": {"type": "string", "format": "uuid"},
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": required,
                        "properties": {
                            **properties,
                            "draftId": {"type": "string", "format": "uuid"},
                            "operationId": {"type": "string", "format": "uuid"},
                            "expectedRevision": {"type": "string", "pattern": "^[1-9][0-9]*$"},
                        },
                    }
                }
            },
        },
    }


base = {key: {"type": "string"} for key in ("projectId", "request", "documentLanguage", "endDate")}
historical = {**base, **{key: {"type": "string"} for key in ("draftId", "proof", "locale")}}


async def execute(request, owner, operation):
    token = correlation_id.set(str(uuid4()))
    try:
        body = await read_json_object(request)
        if request.app.state.settings.llm_workflow:
            command = command_key(request, body)
            try:
                identifier = UUID(body["draftId"])
            except (KeyError, ValueError, TypeError):
                raise WorkflowError("clientUpgradeRequired", 426) from None
            # Submitted analysis/project snapshots and proofs never become authoritative.
            parameters = {
                "operationId": command,
                "expectedRevision": body.get("expectedRevision"),
                "_responseFormat": operation,
                "_legacyRequest": body.get("request"),
                "_legacyProject": body.get("projectId"),
                "_legacyTone": body.get("tone"),
            }
            if operation == "analyze":
                parameters.update(
                    locale=resolve_locale(request).value,
                    documentLanguage=body.get("documentLanguage"),
                )
            elif operation == "materials":
                parameters["language"] = body.get("clientLanguage")
            return await admit_response(
                request,
                UUID(owner["id"]),
                identifier,
                {
                    "analyze": "check",
                    "reply": "regenerate",
                    "materials": "translate",
                    "estimate": "estimate",
                }[operation],
                parameters,
            )
        service = generation_service(request)
        locale = resolve_locale(request)
        if operation == "analyze":
            command = parse_analyze(body)

            async def work():
                outcome = await service.analyze(owner["id"], command, locale)
                return {
                    "result": analysis_to_wire(outcome.result),
                    "projectSnapshot": snapshot_to_wire(outcome.project_snapshot),
                    "proof": outcome.proof,
                }
        elif operation == "reply":
            command = parse_reply(body)

            async def work():
                outcome = await service.regenerate_reply(owner["id"], command, locale)
                return {"reply": outcome.reply}
        elif operation == "materials":
            command = parse_materials(body)

            async def work():
                outcome = await service.translate_materials(owner["id"], command, locale)
                return {"materials": materials_to_wire(outcome.materials)}
        else:
            command = parse_estimate(body)

            async def work():
                outcome = await EstimateChangeOrder(service).execute(owner["id"], command, locale)
                return {"result": analysis_to_wire(outcome.result)}

        response = GenerationJSONResponse(await run_connected(request, work()))
        if operation == "analyze":
            response.headers["Cache-Control"] = "private, no-store"
    except (GenerationError, WorkflowError) as error:
        response = JSONResponse({"error": error.code}, status_code=error.status)
    except ApiError as error:
        response = JSONResponse({"error": error.code.value}, status_code=error.status)
    except Exception:
        log_event("workflow_failed", operation=operation, category="request_failed", status=500)
        response = JSONResponse({"error": "errors.requestFailed"}, status_code=500)
    finally:
        identifier = correlation_id.get()
        correlation_id.reset(token)
    response.headers["x-request-id"] = identifier
    return response


@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    responses={202: {"model": PendingLlmOperation}},
    openapi_extra=request_contract(["projectId", "request"], base),
)
async def analyze(request: Request, owner: Owner):
    return await execute(request, owner, "analyze")


@router.post(
    "/api/replies/regenerate",
    response_model=ReplyResponse,
    responses={202: {"model": PendingLlmOperation}},
    openapi_extra=request_contract(
        ["projectId", "request", "tone", "previousReply"],
        {
            **base,
            "tone": {"type": "string", "enum": ["warm", "neutral", "firm"]},
            "previousReply": {"type": "string"},
        },
    ),
)
async def reply(request: Request, owner: Owner):
    return await execute(request, owner, "reply")


@router.post(
    "/api/client-materials/language",
    response_model=MaterialsResponse,
    responses={202: {"model": PendingLlmOperation}},
    openapi_extra=request_contract(
        ["projectId", "request", "clientLanguage", "analysis"],
        {
            **historical,
            "historyId": {"type": "string"},
            "clientLanguage": {"type": "string"},
            "analysis": {"type": "object"},
        },
    ),
)
async def materials(request: Request, owner: Owner):
    return await execute(request, owner, "materials")


@router.post(
    "/api/change-orders/estimate",
    response_model=EstimateResponse,
    responses={202: {"model": PendingLlmOperation}},
    openapi_extra=request_contract(["projectId", "request"], historical),
)
async def estimate(request: Request, owner: Owner):
    return await execute(request, owner, "estimate")
