from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from scope_guard.api.cancellation import run_connected
from scope_guard.api.contracts import (
    AnalyzeResponse,
    ErrorResponse,
    EstimateResponse,
    MaterialsResponse,
    ReplyResponse,
)
from scope_guard.api.dependencies import current_owner, generation_service
from scope_guard.api.errors import ApiError, read_json_object
from scope_guard.api.generation_input import (
    parse_analyze,
    parse_estimate,
    parse_materials,
    parse_reply,
)
from scope_guard.api.generation_output import analysis_to_wire, materials_to_wire, snapshot_to_wire
from scope_guard.api.locale import resolve_locale
from scope_guard.core.js_compat import stringify
from scope_guard.infrastructure.llm.openai import correlation_id, log_event
from scope_guard.modules.analysis.domain import GenerationError
from scope_guard.modules.change_orders.use_cases import EstimateChangeOrder

router = APIRouter(
    tags=["generation"],
    responses={code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 429, 502, 503)},
)
Owner = Annotated[dict[str, str], Depends(current_owner)]


class GenerationJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return stringify(content).encode("utf-8")


def request_contract(required, properties):
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object", "required": required, "properties": properties}
                }
            },
        }
    }


base = {key: {"type": "string"} for key in ("projectId", "request", "documentLanguage", "endDate")}
historical = {**base, **{key: {"type": "string"} for key in ("draftId", "proof", "locale")}}


async def execute(request, owner, operation):
    token = correlation_id.set(str(uuid4()))
    try:
        body = await read_json_object(request)
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
    except GenerationError as error:
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
    openapi_extra=request_contract(["projectId", "request"], base),
)
async def analyze(request: Request, owner: Owner):
    return await execute(request, owner, "analyze")


@router.post(
    "/api/replies/regenerate",
    response_model=ReplyResponse,
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
    openapi_extra=request_contract(["projectId", "request"], historical),
)
async def estimate(request: Request, owner: Owner):
    return await execute(request, owner, "estimate")
