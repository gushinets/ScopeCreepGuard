from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from scope_guard.services.drafts.workflow import WorkflowService
from starlette.responses import Response

from scope_guard_api.dependencies import current_owner, workflow_service
from scope_guard_api.schemas.workflow import (
    AgreementResponse,
    AgreementsResponse,
    AnalysisResponse,
    DraftResponse,
    ExportRequest,
    ExportResponse,
    ExportsResponse,
    Feedback,
    HistoriesResponse,
    HistoryResponse,
    Operation,
    ProjectResponse,
    ProjectsResponse,
    ProjectUpdate,
    ProjectWrite,
    RevisionResponse,
    RevisionsResponse,
    RunAnalysis,
    SaveWorkingDraft,
    TranslateWorkingDraft,
    VersionedOperation,
)

router = APIRouter(prefix="/api/v2", tags=["persistent-workflow"])
Owner = Annotated[dict[str, str], Depends(current_owner)]
Service = Annotated[WorkflowService, Depends(workflow_service)]


@router.get(
    "/legacy-drafts/{identifier}",
    response_model=RevisionResponse,
    response_model_exclude_unset=True,
)
async def legacy_revision(identifier: UUID, owner: Owner, service: Service):
    return {"revision": await service.legacy_revision(UUID(owner["id"]), identifier)}


@router.get("/projects", response_model=ProjectsResponse)
async def projects(owner: Owner, service: Service, archived: bool = False):
    return {"projects": await service.projects(UUID(owner["id"]), archived)}


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectWrite, owner: Owner, service: Service):
    return {"project": await service.create_project(UUID(owner["id"]), body.to_wire())}


@router.get("/projects/{identifier}", response_model=ProjectResponse)
async def project(identifier: UUID, owner: Owner, service: Service):
    return {"project": await service.project(UUID(owner["id"]), identifier)}


@router.patch("/projects/{identifier}", response_model=ProjectResponse)
async def update_project(identifier: UUID, body: ProjectUpdate, owner: Owner, service: Service):
    return {"project": await service.update_project(UUID(owner["id"]), identifier, body.to_wire())}


@router.delete("/projects/{identifier}")
async def archive_project(identifier: UUID, owner: Owner, service: Service):
    await service.archive_project(UUID(owner["id"]), identifier)
    return {"ok": True}


@router.get(
    "/projects/{identifier}/draft", response_model=DraftResponse, response_model_exclude_unset=True
)
async def project_draft(identifier: UUID, owner: Owner, service: Service):
    return {"draft": await service.project_draft(UUID(owner["id"]), identifier)}


@router.get("/drafts/{identifier}", response_model=DraftResponse, response_model_exclude_unset=True)
async def draft(identifier: UUID, owner: Owner, service: Service):
    return {"draft": await service.draft(UUID(owner["id"]), identifier)}


@router.put("/drafts/{identifier}", response_model=DraftResponse, response_model_exclude_unset=True)
async def save_draft(identifier: UUID, body: SaveWorkingDraft, owner: Owner, service: Service):
    return {"draft": await service.save(UUID(owner["id"]), identifier, body.to_wire())}


@router.post(
    "/drafts/{identifier}/clear", response_model=DraftResponse, response_model_exclude_unset=True
)
async def clear_draft(identifier: UUID, body: VersionedOperation, owner: Owner, service: Service):
    return {"draft": await service.clear(UUID(owner["id"]), identifier, body.to_wire())}


@router.get(
    "/drafts/{identifier}/revisions",
    response_model=RevisionsResponse,
    response_model_exclude_unset=True,
)
async def revisions(identifier: UUID, owner: Owner, service: Service):
    return {"revisions": await service.revisions(UUID(owner["id"]), identifier)}


@router.post(
    "/drafts/{identifier}/revisions/{number}/restore",
    response_model=DraftResponse,
    response_model_exclude_unset=True,
)
async def restore(
    identifier: UUID, number: int, body: VersionedOperation, owner: Owner, service: Service
):
    return {"draft": await service.restore(UUID(owner["id"]), identifier, number, body.to_wire())}


@router.post(
    "/drafts/{identifier}/analyses",
    response_model=AnalysisResponse,
    response_model_exclude_unset=True,
)
async def analyze(identifier: UUID, body: RunAnalysis, owner: Owner, service: Service):
    return await service.analyze(UUID(owner["id"]), identifier, body.to_wire())


@router.get("/analyses/{identifier}")
async def run(identifier: UUID, owner: Owner, service: Service):
    return {"analysisRun": await service.run(UUID(owner["id"]), identifier)}


@router.post(
    "/drafts/{identifier}/estimate",
    response_model=AnalysisResponse,
    response_model_exclude_unset=True,
)
async def estimate(identifier: UUID, body: VersionedOperation, owner: Owner, service: Service):
    return await service.estimate(UUID(owner["id"]), identifier, body.to_wire())


@router.post(
    "/analyses/{identifier}/apply",
    response_model=AnalysisResponse,
    response_model_exclude_unset=True,
)
async def apply(identifier: UUID, owner: Owner, service: Service):
    return await service.apply_analysis(UUID(owner["id"]), identifier)


@router.post(
    "/drafts/{identifier}/regenerate",
    response_model=DraftResponse,
    response_model_exclude_unset=True,
)
async def regenerate(identifier: UUID, body: VersionedOperation, owner: Owner, service: Service):
    return {
        "draft": await service.generate(UUID(owner["id"]), identifier, "regenerate", body.to_wire())
    }


@router.post(
    "/drafts/{identifier}/translate",
    response_model=DraftResponse,
    response_model_exclude_unset=True,
)
async def translate(identifier: UUID, body: TranslateWorkingDraft, owner: Owner, service: Service):
    return {
        "draft": await service.generate(UUID(owner["id"]), identifier, "translate", body.to_wire())
    }


@router.post(
    "/drafts/{identifier}/history",
    response_model=HistoryResponse,
    response_model_exclude_unset=True,
)
async def complete(identifier: UUID, body: VersionedOperation, owner: Owner, service: Service):
    return {"entry": await service.complete(UUID(owner["id"]), identifier, body.to_wire())}


@router.get(
    "/projects/{identifier}/history",
    response_model=HistoriesResponse,
    response_model_exclude_unset=True,
)
async def histories(identifier: UUID, owner: Owner, service: Service):
    return {"entries": await service.histories(UUID(owner["id"]), identifier)}


@router.get(
    "/history/{identifier}", response_model=HistoryResponse, response_model_exclude_unset=True
)
async def history(identifier: UUID, owner: Owner, service: Service):
    return {"entry": await service.history(UUID(owner["id"]), identifier)}


@router.post("/history/{identifier}/change-orders", response_model=AgreementResponse)
async def finalize(identifier: UUID, body: Operation, owner: Owner, service: Service):
    return {"changeOrder": await service.finalize(UUID(owner["id"]), identifier, body.to_wire())}


@router.get("/history/{identifier}/change-orders", response_model=AgreementsResponse)
async def agreements(identifier: UUID, owner: Owner, service: Service):
    return {"changeOrders": await service.agreements(UUID(owner["id"]), identifier)}


@router.get(
    "/change-orders/{identifier}",
    response_model=AgreementResponse,
    response_model_exclude_unset=True,
)
async def agreement(identifier: UUID, owner: Owner, service: Service):
    return {"changeOrder": await service.agreement(UUID(owner["id"]), identifier)}


@router.post(
    "/change-orders/{identifier}/void",
    response_model=AgreementResponse,
    response_model_exclude_unset=True,
)
async def void(identifier: UUID, body: VersionedOperation, owner: Owner, service: Service):
    return {"changeOrder": await service.void(UUID(owner["id"]), identifier, body.to_wire())}


@router.post("/change-orders/{identifier}/exports", response_model=ExportResponse, status_code=202)
async def create_export(identifier: UUID, body: ExportRequest, owner: Owner, service: Service):
    return {"export": await service.create_export(UUID(owner["id"]), identifier, body.to_wire())}


@router.get("/change-orders/{identifier}/exports", response_model=ExportsResponse)
async def exports(identifier: UUID, owner: Owner, service: Service):
    return {"exports": await service.exports(UUID(owner["id"]), identifier)}


@router.get(
    "/exports/{identifier}", response_model=ExportResponse, response_model_exclude_unset=True
)
async def export(identifier: UUID, owner: Owner, service: Service):
    return {"export": await service.export(UUID(owner["id"]), identifier)}


@router.post("/exports/{identifier}/retry", status_code=202, response_model=ExportResponse)
async def retry(identifier: UUID, body: Operation, owner: Owner, service: Service):
    return {"export": await service.retry_export(UUID(owner["id"]), identifier, body.to_wire())}


@router.get("/exports/{identifier}/download")
async def download(identifier: UUID, owner: Owner, service: Service):
    return Response(
        await service.download(UUID(owner["id"]), identifier),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="change-order-{identifier}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/analyses/{identifier}/evaluation")
async def evaluate(identifier: UUID, body: Feedback, owner: Owner, service: Service):
    return {"evaluation": await service.evaluate(UUID(owner["id"]), identifier, body.to_wire())}
