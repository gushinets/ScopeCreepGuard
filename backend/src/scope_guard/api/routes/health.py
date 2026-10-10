from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from scope_guard.infrastructure.database.session import DatabaseUnavailableError

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
async def ready(request: Request) -> JSONResponse:
    database = getattr(request.app.state, "database", None)
    available = False
    if database is not None:
        try:
            await database.check_connection()
            available = True
        except DatabaseUnavailableError:
            pass
    status = "ok" if available else "unavailable"
    return JSONResponse(
        {"status": status, "database": status},
        status_code=200 if available else 503,
        headers={"Cache-Control": "no-store"},
    )
