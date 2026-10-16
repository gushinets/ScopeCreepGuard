"""Real PostgreSQL tests for ANY-549; only disposable fixture URLs are targets."""

import pytest
from sqlalchemy import create_engine, text

from scope_guard.database.migrations import migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration


def test_generation_uses_saved_edits_and_restoration_checks_context(disposable_url, monkeypatch):
    import asyncio
    import json
    from copy import deepcopy
    from pathlib import Path
    from uuid import UUID, uuid4

    from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
    from scope_guard.database.session import Database
    from scope_guard.domain.analysis.normalization import parse_materials, parse_snapshot
    from scope_guard.domain.drafts.workflow import WorkflowError
    from scope_guard.services.drafts.workflow import WorkflowService

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('generation@example.test','hash') "
                "RETURNING id"
            )
        )
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())

    async def exercise():
        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        class Generator:
            async def analyze(self, value):
                assert database.engine.pool.checkedout() == 0
                return parse_snapshot(fixture["analysis"], "en")

            async def regenerate_reply(self, value):
                assert value.previous_reply == "My saved reply"
                assert value.request == "Add a page"
                assert database.engine.pool.checkedout() == 0
                return "Regenerated saved reply"

            async def translate_materials(self, value):
                assert value.analysis.replies.neutral == "Regenerated saved reply"
                assert value.analysis.change_order.description == "My saved terms"
                return parse_materials(
                    {
                        "clientLanguage": "ru",
                        "replies": {
                            tone: "Переведённый ответ" for tone in ("warm", "neutral", "firm")
                        },
                        "changeOrder": {
                            "description": "Мои условия",
                            "timelineImpact": "Два дня",
                            "rationale": "",
                            "note": "Примечание",
                        },
                    }
                )

        service = WorkflowService(factory, Generator())
        project_body = {**fixture["projectInput"], "currency": "EUR"}
        project = await service.create_project(owner, {**project_body, "operationId": str(uuid4())})
        draft = await service.project_draft(owner, UUID(project["id"]))
        identifier = UUID(draft["id"])

        def operation(state):
            return {"expectedRevision": state["revision"], "operationId": str(uuid4())}

        draft = await service.save(
            owner,
            identifier,
            {
                **operation(draft),
                "changes": {"requestText": "Add a page"},
            },
        )
        draft = (await service.analyze(owner, identifier, {**operation(draft), "locale": "en"}))[
            "draft"
        ]
        original_run = deepcopy(draft["analysisRun"])
        document = deepcopy(draft["draftDocument"])
        document["reply"]["text"] = "My saved reply"
        document["changeOrder"].update(description="My saved terms", additionalCost="333.00")
        draft = await service.save(
            owner,
            identifier,
            {
                **operation(draft),
                "changes": {"draftDocument": document},
            },
        )
        tampered = deepcopy(document)
        tampered["changeOrder"]["aiValues"]["description"] = "forged"
        with pytest.raises(WorkflowError):
            await service.save(
                owner,
                identifier,
                {
                    **operation(draft),
                    "changes": {"draftDocument": tampered},
                },
            )
        draft = await service.generate(owner, identifier, "regenerate", operation(draft))
        draft = await service.generate(
            owner, identifier, "translate", {**operation(draft), "language": "ru"}
        )
        assert draft["draftDocument"]["changeOrder"]["additionalCost"] == "333.00"
        estimate = await service.estimate(owner, identifier, operation(draft))
        assert estimate["analysisRun"]["promptVersion"] == "analysis-v1"
        assert estimate["analysisRun"]["purpose"] == "estimate"
        draft = estimate["draft"]
        assert draft["draftDocument"]["changeOrder"]["additionalCost"] == "333.00"
        assert draft["lastAnalysisRunId"] == original_run["id"]
        assert (await service.run(owner, UUID(original_run["id"])))[
            "resultSnapshot"
        ] == original_run["resultSnapshot"]
        saved_revision = int(draft["revision"])
        cleared = await service.clear(owner, identifier, operation(draft))
        assert cleared["id"] == draft["id"]
        restored = await service.restore(owner, identifier, saved_revision, operation(cleared))
        assert restored["analysisIsStale"] is False
        await service.update_project(
            owner,
            UUID(project["id"]),
            {
                **project_body,
                **operation(restored),
                "scope": "Changed scope",
            },
        )
        current = await service.draft(owner, identifier)
        restored = await service.restore(owner, identifier, saved_revision, operation(current))
        assert restored["analysisIsStale"] is True
        assert await service.histories(owner, UUID(project["id"])) == []
        await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_concurrent_creation_stale_model_and_archive_immutability(disposable_url, monkeypatch):
    import asyncio
    import json
    from pathlib import Path
    from uuid import UUID, uuid4

    from sqlalchemy.exc import IntegrityError

    from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
    from scope_guard.database.session import Database
    from scope_guard.domain.analysis.normalization import parse_snapshot
    from scope_guard.domain.drafts.workflow import WorkflowError
    from scope_guard.services.drafts.workflow import WorkflowService

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('race@example.test','hash') "
                "RETURNING id"
            )
        )
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())

    async def exercise():
        database = Database(normalize_url(disposable_url))
        started, release = asyncio.Event(), asyncio.Event()

        class Generator:
            async def analyze(self, value):
                assert database.engine.pool.checkedout() == 0
                started.set()
                await release.wait()
                return parse_snapshot(fixture["analysis"], "en")

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        service = WorkflowService(factory, Generator())
        creation = {**fixture["projectInput"], "operationId": str(uuid4())}
        first, second = await asyncio.gather(
            service.create_project(owner, creation), service.create_project(owner, creation)
        )
        assert first["id"] == second["id"]
        project = UUID(first["id"])
        draft = await service.project_draft(owner, project)
        identifier = UUID(draft["id"])
        draft = await service.save(
            owner,
            identifier,
            {
                "expectedRevision": draft["revision"],
                "operationId": str(uuid4()),
                "changes": {"requestText": "Original request"},
            },
        )
        task = asyncio.create_task(
            service.analyze(
                owner,
                identifier,
                {
                    "expectedRevision": draft["revision"],
                    "operationId": str(uuid4()),
                    "locale": "en",
                },
            )
        )
        await started.wait()
        changed = await service.save(
            owner,
            identifier,
            {
                "expectedRevision": draft["revision"],
                "operationId": str(uuid4()),
                "changes": {"requestText": "New request while generating"},
            },
        )
        release.set()
        outcome = await task
        assert outcome["analysisRun"]["status"] == "succeeded"
        assert outcome["applied"] is False
        assert (await service.draft(owner, identifier))[
            "requestText"
        ] == "New request while generating"
        draft = (
            await service.analyze(
                owner,
                identifier,
                {
                    "expectedRevision": changed["revision"],
                    "operationId": str(uuid4()),
                    "locale": "en",
                },
            )
        )["draft"]
        history = await service.complete(
            owner, identifier, {"expectedRevision": draft["revision"], "operationId": str(uuid4())}
        )
        before = history["checkSnapshot"]
        other_project = await service.create_project(
            owner,
            {
                **fixture["projectInput"],
                "name": "Other project",
                "operationId": str(uuid4()),
            },
        )
        other_draft = await service.project_draft(owner, UUID(other_project["id"]))
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE drafts SET last_analysis_run_id=:run WHERE id=:draft"),
                    {"run": draft["lastAnalysisRunId"], "draft": other_draft["id"]},
                )
        updated = await service.update_project(
            owner,
            project,
            {
                **fixture["projectInput"],
                "scope": "Changed project scope",
                "expectedRevision": draft["revision"],
                "operationId": str(uuid4()),
            },
        )
        assert updated["scope"] == "Changed project scope"
        assert [entry["id"] for entry in updated["history"]] == [history["id"]]
        assert (await service.draft(owner, identifier))["analysisIsStale"] is True
        assert (await service.history(owner, UUID(history["id"])))["checkSnapshot"] == before
        with pytest.raises(WorkflowError) as stale:
            current = await service.draft(owner, identifier)
            await service.complete(
                owner,
                identifier,
                {"expectedRevision": current["revision"], "operationId": str(uuid4())},
            )
        assert stale.value.code == "errors.analysisStale"
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE history_entries SET summary='overwrite' WHERE id=:id"),
                    {"id": history["id"]},
                )
        async with factory() as work:
            current = await work.workflow.draft(owner, identifier)
            await work.workflow.save(
                owner,
                identifier,
                int(current["revision"]),
                uuid4(),
                "rollback",
                {"requestText": "never committed"},
                "manual_save",
                {},
            )
            # No commit: UoW must roll back all three related writes.
        assert (await service.draft(owner, identifier))["requestText"] == current["requestText"]
        await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_legacy_multiple_drafts_preserve_ids_and_missing_provenance(disposable_url, monkeypatch):
    import json
    from pathlib import Path
    from uuid import uuid4

    from scope_guard.database.workflow_backfill import backfill

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())
    originals = {}
    with engine.begin() as connection:
        migrate(connection)
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('legacy@example.test','hash'"
                ") RETURNING id"
            )
        )
        project = connection.scalar(
            text(
                "INSERT INTO projects(user_id,name,industry,scope) VALUES(:owner,'Legacy','"
                "Design','Current scope differs') RETURNING id"
            ),
            {"owner": owner},
        )
        histories = []
        for index in range(2):
            history = connection.scalar(
                text(
                    "INSERT INTO history_entries(project_id,date,request,verdict,summary) V"
                    "ALUES(:project,'2026-01-01',:request,'out_of_scope','Old result') RETU"
                    "RNING id"
                ),
                {"project": project, "request": f"Request {index}"},
            )
            histories.append(history)
            identifier = uuid4()
            connection.execute(
                text(
                    "INSERT INTO drafts(id,project_id,history_entry_id,idempotency_key,proj"
                    "ect_snapshot,analysis_snapshot,draft_document,locale,client_material_l"
                    "anguage,updated_at) VALUES(:id,:project,:history,:key,CAST(:snapshot A"
                    "S jsonb),CAST(:analysis AS jsonb),CAST(:doc AS jsonb),'en','en',:updat"
                    "ed)"
                ),
                {
                    "id": identifier,
                    "project": project,
                    "history": history,
                    "key": uuid4(),
                    "snapshot": json.dumps(fixture["snapshot"]) if index == 0 else None,
                    "analysis": json.dumps(fixture["analysis"]),
                    "doc": json.dumps(fixture["document"]),
                    "updated": f"2026-01-0{index + 1}T00:00:00Z",
                },
            )
            originals[str(identifier)] = connection.scalar(
                text("SELECT to_jsonb(d) FROM drafts d WHERE id=:id"), {"id": identifier}
            )
        evaluation = connection.scalar(
            text(
                "INSERT INTO evaluation_cases(user_id,history_entry_id,scope,request,ai_ver"
                "dict,ai_reasoning,accuracy,industry) VALUES(:owner,:history,'Historical sc"
                "ope','Old request','out_of_scope','Old reasoning','debatable','Design') RE"
                "TURNING id"
            ),
            {"owner": owner, "history": histories[0]},
        )
        migrate(connection, target="0002_workflow_expand")
    assert backfill(engine) == 1
    assert backfill(engine) == 0
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        imported = connection.execute(
            text("SELECT id,state_snapshot FROM draft_revisions WHERE reason='legacy_import'")
        ).all()
        assert {str(row[0]) for row in imported} == set(originals)
        for identifier, snapshot in imported:
            assert snapshot["legacy"] == originals[str(identifier)]
            assert snapshot["importOrderingOnly"] is True
        selected = connection.scalar(
            text("SELECT to_jsonb(d) FROM drafts d WHERE project_id=:id"), {"id": project}
        )
        assert selected["id"] == list(originals)[1]
        assert selected["analysis_is_stale"] is True
        assert connection.scalar(text("SELECT count(*) FROM analysis_runs")) == 0
        assert (
            connection.scalar(
                text("SELECT history_entry_id FROM evaluation_cases WHERE id=:id"),
                {"id": evaluation},
            )
            == histories[0]
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM history_entries WHERE source_kind='legacy_unverif"
                    "ied' AND completed_at IS NULL"
                )
            )
            == 2
        )
    engine.dispose()


def test_saved_fixture_http_workflow_and_restart_safe_export(disposable_url, monkeypatch):
    import asyncio
    import json
    from pathlib import Path
    from uuid import UUID, uuid4

    import httpx
    from pydantic import SecretStr
    from scope_guard_api.main import create_app

    from scope_guard.core.config import Settings
    from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
    from scope_guard.domain.analysis.normalization import parse_snapshot
    from scope_guard.integrations.storage.filesystem import FilesystemObjectStorage
    from scope_guard.services.documents.export_worker import ExportWorker

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())

    class Generator:
        async def analyze(self, value):
            return parse_snapshot(fixture["analysis"], "en")

        async def close(self):
            pass

    class Renderer:
        async def render(self, source):
            assert source.editor.get("description") == "Extra page"
            return b"%PDF-1.4\nimmutable archived bytes"

    async def exercise():
        app = create_app(
            Settings(
                _env_file=None,
                workflow_v2=True,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("workflow-test-secret-at-least-32-characters"),
            )
        )
        app.state.generator = Generator()
        root = Path(__file__).parents[3] / "output" / "export-integration" / uuid4().hex
        app.state.export_storage = FilesystemObjectStorage(root)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            identity = await client.post(
                "/api/auth/register", json={"email": "http@example.test", "password": "12345678"}
            )
            assert identity.status_code == 201
            owner = UUID(identity.json()["user"]["id"])
            project_response = await client.post(
                "/api/v2/projects", json={**fixture["projectInput"], "operationId": str(uuid4())}
            )
            assert project_response.status_code == 201, project_response.text
            project = project_response.json()["project"]
            draft = (await client.get(f"/api/v2/projects/{project['id']}/draft")).json()["draft"]
            draft = (
                await client.put(
                    f"/api/v2/drafts/{draft['id']}",
                    json={
                        "expectedRevision": draft["revision"],
                        "operationId": str(uuid4()),
                        "changes": {"requestText": "Add another page"},
                    },
                )
            ).json()["draft"]
            checked = await client.post(
                f"/api/v2/drafts/{draft['id']}/analyses",
                json={
                    "expectedRevision": draft["revision"],
                    "operationId": str(uuid4()),
                    "locale": "en",
                },
            )
            assert checked.status_code == 503, checked.text
            assert checked.json() == {"error": "errors.workflowUnavailable"}
            # Explicit synthetic saved fixture for export/read/edit compatibility.
            # This is not a successful public generation journey in retired mode.
            from scope_guard.services.drafts.workflow import WorkflowService

            def seed_factory():
                return WorkflowUnitOfWork(app.state.database.new_uow())

            draft = (
                await WorkflowService(seed_factory, app.state.generator).analyze(
                    owner,
                    UUID(draft["id"]),
                    {
                        "expectedRevision": draft["revision"],
                        "operationId": str(uuid4()),
                        "locale": "en",
                    },
                )
            )["draft"]
            edited = draft["draftDocument"]
            edited["reply"]["text"] = "Edited after analysis"
            edited_response = await client.put(
                f"/api/v2/drafts/{draft['id']}",
                json={
                    "expectedRevision": draft["revision"],
                    "operationId": str(uuid4()),
                    "changes": {"draftDocument": edited},
                },
            )
            assert edited_response.status_code == 200, edited_response.text
            draft = edited_response.json()["draft"]
            history = (
                await client.post(
                    f"/api/v2/drafts/{draft['id']}/history",
                    json={"expectedRevision": draft["revision"], "operationId": str(uuid4())},
                )
            ).json()["entry"]
            agreement = (
                await client.post(
                    f"/api/v2/history/{history['id']}/change-orders",
                    json={"operationId": str(uuid4())},
                )
            ).json()["changeOrder"]
            export_response = await client.post(
                f"/api/v2/change-orders/{agreement['id']}/exports",
                json={"operationId": str(uuid4())},
            )
            assert export_response.status_code == 202, export_response.text
            export = export_response.json()["export"]

            def factory():
                return WorkflowUnitOfWork(app.state.database.new_uow())

            worker = ExportWorker(factory, FilesystemObjectStorage(root), Renderer())
            assert await worker.process_one()
            assert not await ExportWorker(
                factory, FilesystemObjectStorage(root), Renderer()
            ).process_one()
            first = await client.get(f"/api/v2/exports/{export['id']}/download")
            second = await client.get(f"/api/v2/exports/{export['id']}/download")
            assert first.status_code == second.status_code == 200
            assert first.content == second.content == b"%PDF-1.4\nimmutable archived bytes"
            async with factory() as work:
                assert (await work.workflow.export(owner, UUID(export["id"])))["attemptCount"] == 1
            # A lost worker lease is reclaimed; the old worker cannot commit over it.
            extra = (
                await client.post(
                    f"/api/v2/change-orders/{agreement['id']}/exports",
                    json={"operationId": str(uuid4())},
                )
            ).json()["export"]
            async with factory() as work:
                abandoned = await work.workflow.claim_export()
                assert abandoned["id"] == extra["id"]
                await work.commit()
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE document_exports SET lease_expires_at=now()-interval '1 second' "
                        "WHERE id=:id"
                    ),
                    {"id": extra["id"]},
                )
            async with factory() as work:
                await work.workflow.recover()
                replacement = await work.workflow.claim_export()
                assert replacement["attemptCount"] == 2
                assert not await work.workflow.export_outcome(
                    abandoned,
                    {
                        "objectKey": "never",
                        "checksum": "wrong",
                        "mimeType": "application/pdf",
                        "sizeBytes": 1,
                    },
                    None,
                )
                assert await work.workflow.export_outcome(replacement, None, "test_failure")
                await work.commit()
            retry_body = {"operationId": str(uuid4())}
            assert (
                await client.post(f"/api/v2/exports/{extra['id']}/retry", json=retry_body)
            ).status_code == 202
            assert (
                await client.post(f"/api/v2/exports/{extra['id']}/retry", json=retry_body)
            ).status_code == 202
            reused = await client.post(f"/api/v2/exports/{export['id']}/retry", json=retry_body)
            assert reused.status_code == 409
            assert reused.json()["error"] == "errors.operationMismatch"
            assert await worker.process_one()
            assert (
                await client.get(f"/api/v2/exports/{extra['id']}/download")
            ).content == first.content
            import os
            from datetime import UTC, datetime, timedelta

            orphan_key = f"exports/scg-{uuid4()}/1.pdf"
            await worker.storage.put(orphan_key, b"orphan")
            old_time = (datetime.now(UTC) - timedelta(days=2)).timestamp()
            os.utime(root / orphan_key, (old_time, old_time))
            assert await worker.sweep_orphans() == 1
            async with factory() as work:
                ready = await work.workflow.export(owner, UUID(export["id"]))
            assert await worker.storage.get(ready["objectKey"]) == first.content
            await client.delete(f"/api/v2/projects/{project['id']}")
            assert (
                await client.get(f"/api/v2/exports/{export['id']}/download")
            ).content == first.content
            assert await worker.expire_ready(datetime.now(UTC) + timedelta(seconds=1)) == 2
            assert (await client.get(f"/api/v2/exports/{export['id']}/download")).status_code == 409
            assert (await client.get(f"/api/v2/exports/{export['id']}")).json()["export"][
                "status"
            ] == "expired"
            foreign = httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test")
            async with foreign:
                await foreign.post(
                    "/api/auth/register",
                    json={"email": "foreign@example.test", "password": "12345678"},
                )
                assert (
                    await foreign.get(f"/api/v2/exports/{export['id']}/download")
                ).status_code == 404
                for path in (
                    f"drafts/{draft['id']}",
                    f"history/{history['id']}",
                    f"change-orders/{agreement['id']}",
                ):
                    assert (await foreign.get(f"/api/v2/{path}")).status_code == 404

    asyncio.run(exercise())
    engine.dispose()


def test_expansion_and_resumable_backfill(disposable_url, monkeypatch):
    engine = create_engine(normalize_url(disposable_url))
    monkeypatch.chdir(__import__("pathlib").Path(__file__).resolve().parents[2])
    with engine.begin() as connection:
        migrate(connection, target="0002_workflow_expand")
        assert connection.scalar(text("SELECT to_regclass('public.analysis_runs')"))
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('workflow@example."
                "test','hash') RETURNING id"
            )
        )
        project = connection.scalar(
            text(
                "INSERT INTO projects(user_id,name,industry,scope) VALUES(:owner,"
                "'Example','Design','Original scope') RETURNING id"
            ),
            {"owner": owner},
        )
    from scope_guard.database.workflow_backfill import backfill, verify_backfill

    assert backfill(engine) == 1
    assert backfill(engine) == 0
    with engine.begin() as connection:
        verify_backfill(connection)
        assert (
            connection.scalar(
                text("SELECT count(*) FROM drafts WHERE project_id=:project AND revision=1"),
                {"project": project},
            )
            == 1
        )
        migrate(connection, target="0003_workflow_constraints")
        migrate(connection, target="0004_workflow_retire")
        assert connection.scalar(text("SELECT count(*) FROM draft_revisions")) == 1
    engine.dispose()


def test_completed_check_archive_and_agreement_are_independent(disposable_url, monkeypatch):
    import asyncio
    import json
    from pathlib import Path
    from uuid import UUID, uuid4

    from scope_guard.database.session import Database
    from scope_guard.domain.analysis.normalization import parse_snapshot

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('complete@example."
                "test','hash') RETURNING id"
            )
        )
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())

    class Generator:
        async def analyze(self, value):
            assert value.request == "Add another page"
            return parse_snapshot(fixture["analysis"], "en")

    class Limiter:
        def allow(self, *_):
            return True

    async def exercise():
        from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
        from scope_guard.services.drafts.workflow import WorkflowService

        database = Database(normalize_url(disposable_url))
        service = WorkflowService(
            lambda: WorkflowUnitOfWork(database.new_uow()), Generator(), Limiter()
        )
        project = await service.create_project(
            owner, {**fixture["projectInput"], "operationId": str(uuid4())}
        )
        draft = await service.project_draft(owner, UUID(project["id"]))
        draft = await service.save(
            owner,
            UUID(draft["id"]),
            {
                "expectedRevision": draft["revision"],
                "operationId": str(uuid4()),
                "changes": {"requestText": "Add another page"},
            },
        )
        outcome = await service.analyze(
            owner,
            UUID(draft["id"]),
            {"expectedRevision": draft["revision"], "operationId": str(uuid4()), "locale": "en"},
        )
        draft = outcome["draft"]
        assert await service.histories(owner, UUID(project["id"])) == []
        parameters = {"expectedRevision": draft["revision"], "operationId": str(uuid4())}
        history = await service.complete(owner, UUID(draft["id"]), parameters)
        assert (await service.complete(owner, UUID(draft["id"]), parameters))["id"] == history["id"]
        alias = {"expectedRevision": draft["revision"], "operationId": str(uuid4())}
        assert (await service.complete(owner, UUID(draft["id"]), alias))["id"] == history["id"]
        repeats = await asyncio.gather(
            *(
                service.complete(
                    owner, UUID(draft["id"]), {**parameters, "operationId": str(uuid4())}
                )
                for _ in range(3)
            )
        )
        assert {entry["id"] for entry in repeats} == {history["id"]}
        assert len(await service.histories(owner, UUID(project["id"]))) == 1
        from scope_guard.domain.drafts.workflow import WorkflowError

        with pytest.raises(WorkflowError) as mismatch:
            await service.complete(owner, UUID(draft["id"]), {**alias, "expectedRevision": "999"})
        assert mismatch.value.code == "errors.operationMismatch"
        agreement = await service.finalize(
            owner, UUID(history["id"]), {"operationId": str(uuid4())}
        )
        assert agreement["status"] == "finalized"
        document = {
            **draft["draftDocument"],
            "reply": {**draft["draftDocument"]["reply"], "text": "Manual revised reply"},
        }
        edited = await service.save(
            owner,
            UUID(draft["id"]),
            {
                "expectedRevision": draft["revision"],
                "operationId": str(uuid4()),
                "changes": {"draftDocument": document},
            },
        )
        edited_entry = await service.complete(
            owner,
            UUID(draft["id"]),
            {
                "expectedRevision": edited["revision"],
                "operationId": str(uuid4()),
            },
        )
        assert edited_entry["id"] != history["id"]
        assert (
            edited_entry["checkSnapshot"]["draftDocument"]["reply"]["text"]
            == "Manual revised reply"
        )
        assert len(await service.histories(owner, UUID(project["id"]))) == 2
        assert (await service.history(owner, UUID(history["id"])))["checkSnapshot"] == history[
            "checkSnapshot"
        ]
        assert (await service.complete(owner, UUID(draft["id"]), alias))["id"] == history["id"]
        await service.clear(
            owner,
            UUID(draft["id"]),
            {"expectedRevision": edited["revision"], "operationId": str(uuid4())},
        )
        archived = await service.history(owner, UUID(history["id"]))
        assert archived["checkSnapshot"]["requestText"] == "Add another page"
        assert archived["sourceDraftRevision"] == draft["revision"]
        assert (await service.agreement(owner, UUID(agreement["id"])))["contentSnapshot"][
            "document"
        ]["description"] == "Extra page"
        await database.close()

    asyncio.run(exercise())
    engine.dispose()


def test_atomic_saves_conflicts_and_completed_retries(disposable_url, monkeypatch):
    import asyncio
    from pathlib import Path
    from uuid import UUID, uuid4

    from scope_guard.database.session import Database
    from scope_guard.domain.drafts.workflow import WorkflowError, operation_hash

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="0004_workflow_retire")
        owner = connection.scalar(
            text(
                "INSERT INTO users(email,password_hash) VALUES('owner@example.tes"
                "t','hash') RETURNING id"
            )
        )

    async def exercise():
        from scope_guard.database.repositories.workflow import WorkflowUnitOfWork

        database = Database(normalize_url(disposable_url))

        def factory():
            return WorkflowUnitOfWork(database.new_uow())

        card = {
            "name": "Example",
            "industry": "Design",
            "scope": "Original",
            "clientName": None,
            "clientEmail": None,
            "endDate": None,
            "startDate": None,
            "pricingModel": None,
            "currency": None,
            "hourlyRate": None,
            "fixedPrice": None,
        }
        key = uuid4()
        async with factory() as work:
            project = await work.workflow.create_project(owner, card, key, operation_hash(card))
            draft = await work.workflow.project_draft(owner, UUID(project["id"]))
            await work.commit()
        operation = uuid4()
        changes = {"requestText": "Add another page"}

        async def save(op, expected=1):
            async with factory() as work:
                saved = await work.workflow.save(
                    owner,
                    UUID(draft["id"]),
                    expected,
                    op,
                    operation_hash(changes),
                    changes,
                    "manual_save",
                    card,
                )
                await work.commit()
                return saved

        saved = await save(operation)
        assert saved["revision"] == "2"
        assert (await save(operation))["revision"] == "2"
        with pytest.raises(WorkflowError) as conflict:
            await save(uuid4())
        assert conflict.value.status == 409
        async with factory() as work:
            assert len(await work.workflow.revisions(owner, UUID(draft["id"]))) == 2
            with pytest.raises(WorkflowError) as missing:
                await work.workflow.draft(uuid4(), UUID(draft["id"]))
            assert missing.value.status == 404
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM history_entries")) == 0
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM activity_events WHERE event_type='manual_save'")
                )
                == 1
            )
        async with factory() as work:
            with pytest.raises(WorkflowError) as mismatch:
                await work.workflow.saved_operation(
                    owner, UUID(draft["id"]), operation, "different"
                )
            assert mismatch.value.code == "errors.operationMismatch"
        concurrent = await asyncio.gather(
            save(uuid4(), 2), save(uuid4(), 2), return_exceptions=True
        )
        assert len([value for value in concurrent if isinstance(value, dict)]) == 1
        rejected = [value for value in concurrent if isinstance(value, WorkflowError)]
        assert len(rejected) == 1 and rejected[0].status == 409
        async with factory() as work:
            assert len(await work.workflow.revisions(owner, UUID(draft["id"]))) == 3
        await database.close()

    asyncio.run(exercise())
    engine.dispose()
