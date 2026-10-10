from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from scope_guard.api.contracts import (
    CreatedDraftResponse,
    DraftEnvelope,
    DraftsResponse,
    ErrorResponse,
)
from scope_guard.api.dependencies import current_owner, draft_service
from scope_guard.api.draft_input import parse_document, parse_envelope, verified_command
from scope_guard.api.errors import ApiError, ErrorCode, log_unexpected, read_json_object
from scope_guard.core.js_compat import stringify
from scope_guard.infrastructure.auth.draft_proofs import UUID_PATTERN, DraftProofs
from scope_guard.modules.analysis.domain import DraftProofBinding
from scope_guard.modules.drafts.schemas import CreateDraftRequest, UpdateDraftRequest
from scope_guard.modules.drafts.serialization import created_to_wire, draft_to_wire, summary_to_wire
from scope_guard.modules.drafts.use_cases import DraftError, DraftService
from scope_guard.modules.drafts.values import StoredDraft

router = APIRouter(
    prefix="/api/drafts",
    tags=["drafts"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 500)},
)
Owner = Annotated[dict[str, str], Depends(current_owner)]
Service = Annotated[DraftService, Depends(draft_service)]
private_responses: dict = {
    status: {
        "headers": {"Cache-Control": {"schema": {"type": "string", "const": "private, no-store"}}}
    }
    for status in (200, 400, 401, 403, 404, 500)
}


async def read_draft_body(request: Request) -> dict:
    try:
        return await read_json_object(request)
    except RecursionError:
        raise ApiError(ErrorCode.request_body_invalid) from None


def json_response(value: dict, status: int = 200) -> Response:
    return Response(
        stringify(value).encode("utf-8"), status_code=status, media_type="application/json"
    )


def failure(error: Exception, code: ErrorCode) -> ApiError:
    if isinstance(error, DraftError):
        return ApiError(ErrorCode(error.code), error.status)
    log_unexpected(error)
    return ApiError(code, 500)


def identifier(value: str) -> UUID:
    if not UUID_PATTERN.fullmatch(value):
        raise ApiError(ErrorCode.draft_not_found, 404)
    return UUID(value)


def body_contract(model):
    schema = model.model_json_schema(by_alias=True)
    definitions = schema.pop("$defs", {})

    # Inline definitions locally, as generation routes do; no dangling component refs.
    def inline(value):
        if isinstance(value, dict):
            if "$ref" in value:
                return inline(definitions[value["$ref"].rsplit("/", 1)[1]])
            return {key: inline(child) for key, child in value.items()}
        if isinstance(value, list):
            return [inline(child) for child in value]
        return value

    return {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": inline(schema)}},
        }
    }


@router.get("", response_model=DraftsResponse, responses=private_responses)
async def list_drafts(owner: Owner, service: Service):
    try:
        return json_response(
            {"drafts": [summary_to_wire(item) for item in await service.list(UUID(owner["id"]))]}
        )
    except Exception as error:
        raise failure(error, ErrorCode.draft_load_failed) from None


@router.get("/{id:path}", response_model=DraftEnvelope, responses=private_responses)
async def get_draft(id: str, owner: Owner, service: Service):
    key = identifier(id)
    try:
        return json_response({"draft": draft_to_wire(await service.get(UUID(owner["id"]), key))})
    except Exception as error:
        raise failure(error, ErrorCode.draft_load_failed) from None


@router.post(
    "",
    response_model=CreatedDraftResponse,
    status_code=201,
    responses={200: {"model": CreatedDraftResponse}},
    openapi_extra=body_contract(CreateDraftRequest),
)
async def create_draft(request: Request, owner: Owner, service: Service):
    body = await read_draft_body(request)
    try:
        envelope = parse_envelope(body)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    try:
        settings = request.app.state.settings
        secret = settings.auth_secret.get_secret_value() if settings.auth_secret else ""
        claims = DraftProofs(secret, request.app.state.clock).verify(
            body.get("proof"),
            DraftProofBinding(owner["id"], envelope.project_id, envelope.request, envelope.locale),
        )
    except ValueError:
        raise ApiError(ErrorCode.draft_proof_invalid) from None
    try:
        command = verified_command(envelope, body.get("draftDocument"), claims)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    try:
        result = await service.create(UUID(owner["id"]), command)
        return json_response(created_to_wire(result), 201 if result.created else 200)
    except Exception as error:
        raise failure(error, ErrorCode.draft_save_failed) from None


@router.put(
    "/{id:path}", response_model=DraftEnvelope, openapi_extra=body_contract(UpdateDraftRequest)
)
async def update_draft(id: str, request: Request, owner: Owner, service: Service):
    key = identifier(id)

    async def read_document(saved: StoredDraft):
        body = await read_draft_body(request)
        try:
            return parse_document(body.get("draftDocument"), saved.locale, saved.analysis_snapshot)
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise ApiError(ErrorCode.request_body_invalid) from None

    try:
        result = await service.update(UUID(owner["id"]), key, read_document)
        return json_response({"draft": draft_to_wire(result)})
    except ApiError:
        raise
    except Exception as error:
        raise failure(error, ErrorCode.draft_save_failed) from None
