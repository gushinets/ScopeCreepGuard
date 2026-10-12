from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scope_guard.services.health.service import HealthService

from scope_guard_api.dependencies import health_service

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/live", response_model=LivenessResponse)
def live() -> LivenessResponse:
    return LivenessResponse()


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unavailable"]


@router.get(
    "/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}}
)
async def ready(service: Annotated[HealthService, Depends(health_service)]) -> JSONResponse:
    available = await service.ready()
    status = "ok" if available else "unavailable"
    return JSONResponse(
        {"status": status, "database": status},
        status_code=200 if available else 503,
        headers={"Cache-Control": "no-store"},
    )
