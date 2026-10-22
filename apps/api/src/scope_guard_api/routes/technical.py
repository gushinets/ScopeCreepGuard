from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from scope_guard.domain.drafts.values import freeze_object
from scope_guard.services.documents.models import DocumentError, DocumentSource
from scope_guard.services.documents.ports import TechnicalError
from scope_guard.services.documents.rendering import DocumentRendering
from scope_guard.services.documents.use_cases import DocumentUseCases
from scope_guard.services.drafts.use_cases import DraftError
from scope_guard.services.scope_extraction.use_cases import ExtractionService
from starlette.responses import Response

from scope_guard_api.cancellation import run_connected
from scope_guard_api.contracts import ErrorResponse
from scope_guard_api.dependencies import (
    current_owner,
    document_renderer,
    document_use_cases,
    extraction_service,
)
from scope_guard_api.draft_input import parse_editor
from scope_guard_api.errors import ApiError, ErrorCode
from scope_guard_api.routes.drafts import body_contract, identifier
from scope_guard_api.schemas.drafts import DraftEditableChangeOrder
from scope_guard_api.schemas.scope_extraction import ExtractionResponse
from scope_guard_api.schemas.shared import WireModel
from scope_guard_api.technical_input import preview_body, scope_upload

router = APIRouter(
    tags=["technical-services"],
    responses={
        status: {"model": ErrorResponse}
        for status in (400, 401, 403, 404, 413, 415, 422, 429, 500, 504)
    },
)
Owner = Annotated[dict[str, str], Depends(current_owner)]
Documents = Annotated[DocumentUseCases, Depends(document_use_cases)]
Renderer = Annotated[DocumentRendering, Depends(document_renderer)]
Extraction = Annotated[ExtractionService, Depends(extraction_service)]


class PreviewBody(WireModel):
    project_id: UUID
    draft_id: UUID | None = None
    change_order: DraftEditableChangeOrder


PDF_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Change Order PDF",
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        "headers": {
            name: {"schema": {"type": "string"}}
            for name in ("Content-Disposition", "Cache-Control")
        },
    }
}


async def render(
    request: Request, source: DocumentSource, key: UUID, renderer: DocumentRendering
) -> Response:
    try:
        result = await run_connected(request, renderer.render(source))
    except (TechnicalError, DocumentError) as error:
        raise ApiError(ErrorCode("errors." + error.code), error.status) from None
    return Response(
        result,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="change-order-{key}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/api/drafts/{draftId}/pdf", response_class=Response, responses=PDF_RESPONSE)
async def saved_pdf(
    draftId: str, request: Request, owner: Owner, documents: Documents, renderer: Renderer
):
    key = identifier(draftId)
    try:
        editor = await documents.saved(UUID(owner["id"]), key)
    except (DraftError, DocumentError) as error:
        code = error.code if error.code.startswith("errors.") else "errors." + error.code
        raise ApiError(ErrorCode(code), error.status) from None
    return await render(request, editor, key, renderer)


@router.post(
    "/api/v2/change-orders/pdf",
    response_class=Response,
    responses=PDF_RESPONSE,
    openapi_extra=body_contract(PreviewBody),
)
@router.post(
    "/api/change-orders/pdf",
    response_class=Response,
    responses=PDF_RESPONSE,
    openapi_extra=body_contract(PreviewBody),
)
async def preview_pdf(request: Request, owner: Owner, documents: Documents, renderer: Renderer):
    body = await preview_body(request)
    try:
        project = UUID(body["projectId"])
        draft = identifier(body["draftId"]) if body.get("draftId") is not None else None
        editor = body["changeOrder"]
        parse_editor(editor)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    try:
        editor = await documents.preview(UUID(owner["id"]), project, draft, freeze_object(editor))
    except DraftError as error:
        raise ApiError(ErrorCode(error.code), error.status) from None
    return await render(request, editor, draft or project, renderer)


@router.post(
    "/api/scope/extract",
    response_model=ExtractionResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                        "additionalProperties": False,
                    }
                }
            },
        }
    },
)
async def scope_extract(request: Request, owner: Owner, service: Extraction):
    name, mime, data = await scope_upload(request)
    try:
        result = await run_connected(request, service.extract(name, mime, data))
    except TechnicalError as error:
        raise ApiError(ErrorCode("errors." + error.code), error.status) from None
    return Response(
        result, media_type="application/json", headers={"Cache-Control": "private, no-store"}
    )
