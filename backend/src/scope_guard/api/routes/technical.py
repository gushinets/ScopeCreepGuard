import base64
import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from scope_guard.api.cancellation import run_connected
from scope_guard.api.contracts import ErrorResponse
from scope_guard.api.dependencies import current_owner, document_use_cases
from scope_guard.api.draft_input import parse_editor
from scope_guard.api.errors import ApiError, ErrorCode
from scope_guard.api.routes.drafts import body_contract, identifier
from scope_guard.api.technical_input import preview_body, scope_upload
from scope_guard.core.contracts import WireModel
from scope_guard.infrastructure.technical.operations import TechnicalError
from scope_guard.modules.change_orders.documents import DocumentUseCases
from scope_guard.modules.drafts.schemas import DraftEditableChangeOrder
from scope_guard.modules.drafts.use_cases import DraftError
from scope_guard.modules.drafts.values import freeze_object, thaw_json
from scope_guard.services.documents.models import DocumentError, DocumentSource
from scope_guard.services.scope_extraction.models import ExtractionResponse

router = APIRouter(
    tags=["technical-services"],
    responses={
        status: {"model": ErrorResponse}
        for status in (400, 401, 403, 404, 413, 415, 422, 429, 500, 504)
    },
)
Owner = Annotated[dict[str, str], Depends(current_owner)]
Documents = Annotated[DocumentUseCases, Depends(document_use_cases)]


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


async def render(request: Request, source: DocumentSource, key: UUID) -> Response:
    editor = thaw_json(source.editor)
    try:
        # Validate explicitly before the isolated renderer; it sees no HTTP state.
        parse_editor(editor)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ApiError(ErrorCode.pdf_document_invalid) from None
    try:
        result = await run_connected(
            request,
            request.app.state.technical_operations.run(
                "pdf",
                json.dumps(
                    {"changeOrder": editor, "projectSnapshot": thaw_json(source.project_snapshot)},
                    ensure_ascii=False,
                ).encode(),
            ),
        )
    except TechnicalError as error:
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
async def saved_pdf(draftId: str, request: Request, owner: Owner, documents: Documents):
    key = identifier(draftId)
    try:
        editor = await documents.saved(UUID(owner["id"]), key)
    except (DraftError, DocumentError) as error:
        code = error.code if error.code.startswith("errors.") else "errors." + error.code
        raise ApiError(ErrorCode(code), error.status) from None
    return await render(request, editor, key)


@router.post(
    "/api/change-orders/pdf",
    response_class=Response,
    responses=PDF_RESPONSE,
    openapi_extra=body_contract(PreviewBody),
)
async def preview_pdf(request: Request, owner: Owner, documents: Documents):
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
    return await render(request, editor, draft or project)


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
async def scope_extract(request: Request, owner: Owner):
    name, mime, data = await scope_upload(request)
    payload = json.dumps(
        {"name": name, "mime": mime, "data": base64.b64encode(data).decode("ascii")}
    ).encode()
    try:
        result = await run_connected(
            request, request.app.state.technical_operations.run("extract", payload)
        )
    except TechnicalError as error:
        raise ApiError(ErrorCode("errors." + error.code), error.status) from None
    return Response(
        result, media_type="application/json", headers={"Cache-Control": "private, no-store"}
    )
