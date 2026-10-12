from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse, Response

from scope_guard.api.contracts import ErrorResponse, EvaluationEnvelope
from scope_guard.api.dependencies import current_owner, evaluation_service
from scope_guard.api.errors import read_json_object
from scope_guard.api.evaluation_input import parse_evaluation
from scope_guard.domain.evaluations.serialization import serialize_jsonl
from scope_guard.services.evaluations.use_cases import EvaluationService

router = APIRouter(
    prefix="/api/evaluations",
    tags=["evaluations"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 500)},
)
Owner = Annotated[dict[str, str], Depends(current_owner)]
Service = Annotated[EvaluationService, Depends(evaluation_service)]
evaluation_contract = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {
                            "type": "object",
                            "required": ["historyEntryId", "accuracy", "aiReasoning"],
                            "properties": {
                                "historyEntryId": {"type": "string", "format": "uuid"},
                                "accuracy": {"type": "string", "const": "correct"},
                                "aiReasoning": {"type": "string"},
                                "humanVerdict": False,
                            },
                        },
                        {
                            "type": "object",
                            "required": ["historyEntryId", "accuracy", "aiReasoning"],
                            "properties": {
                                "historyEntryId": {"type": "string", "format": "uuid"},
                                "accuracy": {"type": "string", "const": "debatable"},
                                "aiReasoning": {"type": "string"},
                                "humanVerdict": False,
                            },
                        },
                        {
                            "type": "object",
                            "required": [
                                "historyEntryId",
                                "accuracy",
                                "aiReasoning",
                                "humanVerdict",
                            ],
                            "properties": {
                                "historyEntryId": {"type": "string", "format": "uuid"},
                                "accuracy": {"type": "string", "const": "wrong"},
                                "aiReasoning": {"type": "string"},
                                "humanVerdict": {
                                    "type": "string",
                                    "enum": ["in_scope", "borderline", "out_of_scope"],
                                },
                            },
                        },
                    ],
                }
            }
        },
    }
}


@router.post("", response_model=EvaluationEnvelope, openapi_extra=evaluation_contract)
async def create_evaluation(request: Request, owner: Owner, service: Service):
    result = await service.label(owner["id"], parse_evaluation(await read_json_object(request)))
    return JSONResponse(
        {
            "evaluation": {
                "id": str(result.id),
                "accuracy": result.accuracy.value,
                "humanVerdict": result.human_verdict.value if result.human_verdict else None,
            }
        }
    )


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {
            "content": {"application/x-ndjson": {"schema": {"type": "string"}}},
            "headers": {
                "Content-Disposition": {
                    "schema": {
                        "type": "string",
                        "const": 'attachment; filename="scope-creep-evaluations.jsonl"',
                    }
                }
            },
        }
    },
)
async def export_evaluations(owner: Owner, service: Service):
    return Response(
        serialize_jsonl(await service.export(owner["id"])),
        headers={
            "Content-Type": "application/x-ndjson; charset=utf-8",
            "Content-Disposition": 'attachment; filename="scope-creep-evaluations.jsonl"',
        },
    )
