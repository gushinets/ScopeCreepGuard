"""Estimate inputs come from an immutable owned Draft revision, never client results."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import Database, normalize_url
from scope_guard.domain.analysis.normalization import parse_snapshot
from scope_guard.domain.change_orders.estimation import commercial_signature
from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.services.drafts.workflow import WorkflowService, generation_context
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "edited,project_deadline", [("2027-02-01", "2026-12-01"), ("", "2026-12-01"), ("", None)]
)
@pytest.mark.parametrize("competing_edit", [False, True])
def test_estimate_deadline_provenance_and_late_application(
    disposable_url, monkeypatch, edited, project_deadline, competing_edit
):
    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) "
                "VALUES('deadline@example.test','hash') RETURNING id"
            )
        )
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())
    effective = edited or project_deadline

    async def exercise():
        database = Database(normalize_url(disposable_url))
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        class Generator:
            async def analyze(self, value):
                assert database.engine.pool.checkedout() == 0
                calls.append(value)
                result = deepcopy(fixture["analysis"])
                if len(calls) > 1:
                    started.set()
                    if competing_edit:
                        await release.wait()
                    result["changeOrder"].update(estimatedHours=8, additionalCost="800")
                return parse_snapshot(result, "en")

        def operation(draft):
            return {"expectedRevision": draft["revision"], "operationId": str(uuid4())}

        service = WorkflowService(factory, Generator())
        project = await service.create_project(
            owner,
            {
                **fixture["projectInput"],
                "currency": "EUR",
                "endDate": project_deadline,
                "operationId": str(uuid4()),
            },
        )
        draft = await service.project_draft(owner, UUID(project["id"]))
        identifier = UUID(draft["id"])
        draft = await service.save(
            owner,
            identifier,
            {
                **operation(draft),
                "changes": {"requestText": "Add another page"},
            },
        )
        draft = (await service.analyze(owner, identifier, {**operation(draft), "locale": "en"}))[
            "draft"
        ]
        original = deepcopy(draft["analysisRun"])
        document = deepcopy(draft["draftDocument"])
        document["changeOrder"].update(
            endDate=edited, additionalCost="333.00", description="Manual terms"
        )
        draft = await service.save(
            owner, identifier, {**operation(draft), "changes": {"draftDocument": document}}
        )
        body = operation(draft)
        task = asyncio.create_task(service.estimate(owner, identifier, body))
        await started.wait()
        if competing_edit:
            changed_document = deepcopy(draft["draftDocument"])
            changed_document["changeOrder"]["endDate"] = "2028-03-01"
            changed = await service.save(
                owner,
                identifier,
                {
                    **operation(draft),
                    "changes": {"draftDocument": changed_document},
                },
            )
            release.set()
        outcome = await task
        assert calls[-1].end_date == effective
        result = outcome["analysisRun"]["resultSnapshot"]
        assert result["commercialSignature"] == commercial_signature(
            generation_context(project["id"], original["projectSnapshot"]),
            effective,
        )
        assert outcome["analysisRun"]["projectSnapshot"]["endDate"] == project_deadline
        assert (await service.project(owner, UUID(project["id"])))["endDate"] == project_deadline
        assert (await service.run(owner, UUID(original["id"])))["resultSnapshot"] == original[
            "resultSnapshot"
        ]
        current = await service.draft(owner, identifier)
        assert current["lastAnalysisRunId"] == original["id"]
        assert current["draftDocument"]["changeOrder"]["additionalCost"] == "333.00"
        assert current["draftDocument"]["changeOrder"]["description"] == "Manual terms"
        if competing_edit:
            assert outcome["applied"] is False
            assert current["revision"] == changed["revision"]
            assert current["draftDocument"]["changeOrder"]["endDate"] == "2028-03-01"
            assert (await service.apply_analysis(owner, UUID(outcome["analysisRun"]["id"])))[
                "applied"
            ] is False
        else:
            assert outcome["applied"] is True
            metadata = current["draftDocument"]["estimate"]
            assert metadata["analysisRunId"] == outcome["analysisRun"]["id"]
            assert metadata["sourceDraftRevision"] == draft["revision"]
            assert metadata["effectiveEndDate"] == effective
            assert metadata["commercialSignature"] == result["commercialSignature"]
            assert metadata["estimateValid"] is True
            assert (await service.estimate(owner, identifier, body))["draft"][
                "revision"
            ] == current["revision"]
            assert len(calls) == 2
            forged = deepcopy(current["draftDocument"])
            forged["estimate"]["commercialSignature"] = "forged"
            with pytest.raises(WorkflowError):
                await service.save(
                    owner, identifier, {**operation(current), "changes": {"draftDocument": forged}}
                )
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
