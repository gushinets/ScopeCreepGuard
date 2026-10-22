from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from scope_guard.services.profiles.service import ProfileService
from starlette.responses import Response

from scope_guard_api.dependencies import current_owner, profile_service
from scope_guard_api.schemas.profiles import (
    OnboardingEvent,
    OnboardingState,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(prefix="/api/v2", tags=["profile"])
Owner = Annotated[dict[str, str], Depends(current_owner)]
Service = Annotated[ProfileService, Depends(profile_service)]


@router.get("/profile/onboarding", response_model=OnboardingState)
async def onboarding(owner: Owner, service: Service):
    return await service.onboarding(UUID(owner["id"]))


@router.post("/profile/onboarding", response_model=OnboardingState)
async def advance_onboarding(body: OnboardingEvent, owner: Owner, service: Service):
    return await service.onboarding(UUID(owner["id"]), body.event)


@router.get("/profile", response_model=ProfileResponse)
async def profile(owner: Owner, service: Service):
    return {"profile": await service.get(UUID(owner["id"]))}


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(body: ProfileUpdate, owner: Owner, service: Service):
    return {"profile": await service.update(UUID(owner["id"]), body.to_wire())}


@router.post("/session/interaction", status_code=204)
async def interaction(owner: Owner, service: Service):
    # This is an interaction observation only, never a success/DAU event.
    await service.observe(UUID(owner["id"]))
    return Response(status_code=204)
