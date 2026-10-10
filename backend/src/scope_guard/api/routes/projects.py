from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from scope_guard.api.contracts import ErrorResponse, OkResponse, ProjectEnvelope, ProjectsResponse
from scope_guard.api.dependencies import current_owner, project_service
from scope_guard.api.errors import read_json_object
from scope_guard.api.project_input import parse_project
from scope_guard.api.project_output import project_to_wire
from scope_guard.modules.projects.domain import ProjectCard
from scope_guard.modules.projects.use_cases import ProjectService

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
Owner = Annotated[dict[str, str], Depends(current_owner)]
Service = Annotated[ProjectService, Depends(project_service)]
body_schema: dict = {
    "type": "object",
    "required": ["name", "scope", "industry", "startDate", "pricingModel", "currency"],
    "properties": {
        "name": {"type": "string"},
        "scope": {"type": "string"},
        "clientName": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "industry": {"type": "string", "enum": ["Development", "Design", "Marketing"]},
        "startDate": {"type": "string", "format": "date"},
        "pricingModel": {"type": "string", "enum": ["hourly", "fixed"]},
        "currency": {"type": "string", "enum": ["RUB", "USD", "EUR"]},
    },
}
# Monetary JSON numbers remain accepted by the legacy parser.
for name in ("hourlyRate", "fixedPrice"):
    body_schema["properties"][name] = {
        "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "null"}]
    }
request_contract = {
    "requestBody": {"required": True, "content": {"application/json": {"schema": body_schema}}}
}


@router.get("", response_model=ProjectsResponse)
async def list_projects(owner: Owner, service: Service):
    return JSONResponse(
        {"projects": [project_to_wire(item) for item in await service.list(owner["id"])]}
    )


@router.post("", response_model=ProjectEnvelope, status_code=201, openapi_extra=request_contract)
async def create_project(request: Request, owner: Owner, service: Service):
    return JSONResponse(
        {"project": project_to_wire(await service.create(owner["id"], await read_card(request)))},
        status_code=201,
    )


@router.get("/{project_id}", response_model=ProjectEnvelope)
async def get_project(project_id: str, owner: Owner, service: Service):
    return JSONResponse({"project": project_to_wire(await service.get(owner["id"], project_id))})


@router.patch("/{project_id}", response_model=ProjectEnvelope, openapi_extra=request_contract)
async def update_project(project_id: str, request: Request, owner: Owner, service: Service):
    result = await service.update(owner["id"], project_id, lambda: read_card(request))
    return JSONResponse({"project": project_to_wire(result)})


@router.delete("/{project_id}", response_model=OkResponse)
async def delete_project(project_id: str, owner: Owner, service: Service):
    await service.delete(owner["id"], project_id)
    return JSONResponse({"ok": True})


async def read_card(request: Request) -> ProjectCard:
    return parse_project(await read_json_object(request))
