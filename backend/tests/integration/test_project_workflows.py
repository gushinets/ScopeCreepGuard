import asyncio
from dataclasses import FrozenInstanceError
from uuid import UUID

import httpx
import pytest
from integration.support import replay_drizzle
from pydantic import SecretStr
from sqlalchemy import text

from scope_guard.api.project_output import project_to_wire
from scope_guard.core.config import Settings
from scope_guard.infrastructure.database.repositories.projects import ProjectUnitOfWork
from scope_guard.main import create_app
from scope_guard.modules.projects.use_cases import ProjectService

pytestmark = pytest.mark.integration
CARD = {
    "name": " Website ",
    "clientName": " Owner ",
    "scope": " Five pages ",
    "industry": "Development",
    "startDate": "2026-10-10",
    "pricingModel": "hourly",
    "currency": "EUR",
    "hourlyRate": "100.20",
    "endDate": "2099-01-01",
}


def test_project_ownership_history_snapshots_and_cascades(disposable_url):
    replay_drizzle(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("project-test-secret"),
            )
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            owners = []
            for email in ("owner@example.test", "other@example.test"):
                response = await client.post(
                    "/api/auth/register", json={"email": email, "password": "12345678"}
                )
                owners.append(
                    (response.json()["user"]["id"], response.headers["set-cookie"].split(";")[0])
                )
            owner, cookie = owners[0]
            foreign, foreign_cookie = owners[1]

            async def call(method, path="/api/projects", body=None, selected=cookie):
                return await client.request(method, path, json=body, headers={"cookie": selected})

            response = await call("POST", body=CARD)
            assert response.status_code == 201
            project = response.json()["project"]
            identifier = project["id"]
            path = "/api/projects/" + identifier
            assert project["name"] == "Website" and project["hourlyRate"] == "100.20"
            assert "lastChecked" not in project and "endDate" not in project
            assert project["fixedPrice"] is None and project["history"] == []
            assert (await call("POST", body={**CARD, "hourlyRate": ""})).json() == {
                "error": "errors.hourlyRateInvalid"
            }
            assert (await call("PATCH", path, {**CARD, "hourlyRate": "0"})).status_code == 400
            assert (await call("GET", path)).json()["project"] == project
            for method in ("GET", "PATCH", "DELETE"):
                assert (await call(method, path, selected=foreign_cookie)).status_code == 404
                assert (await call(method, path, selected="")).status_code == 401
            assert (await call("GET", "/api/projects/malformed")).status_code == 500
            assert (await call("PATCH", path, {})).json() == {"error": "errors.projectNameRequired"}
            assert (await call("POST", body=None, selected="")).status_code == 401
            assert (
                await call("PATCH", "/api/projects/10000000-0000-4000-8000-000000000001", {})
            ).status_code == 404
            async with app.state.database.new_uow() as work:
                old = (
                    await work.session.execute(
                        text(
                            "INSERT INTO history_entries(project_id,date,request,verdict,summary) "
                            "VALUES (:id,'2026-10-01','Old','in_scope','Old summary') RETURNING id"
                        ),
                        {"id": identifier},
                    )
                ).scalar_one()
                linked = (
                    await work.session.execute(
                        text(
                            "INSERT INTO history_entries(project_id,date,request,verdict,summary) "
                            "VALUES (:id,'2026-10-09','New','out_of_scope','New summary') "
                            "RETURNING id"
                        ),
                        {"id": identifier},
                    )
                ).scalar_one()
                draft = (
                    await work.session.execute(
                        text(
                            "INSERT INTO drafts(project_id,history_entry_id,idempotency_key,"
                            "project_snapshot,analysis_snapshot,draft_document,locale,"
                            "client_material_language) "
                            "VALUES (:id,:history,gen_random_uuid(),CAST(:snapshot AS jsonb),"
                            "CAST(:analysis AS jsonb),'{}','en','en') RETURNING id"
                        ),
                        {
                            "id": identifier,
                            "history": linked,
                            "snapshot": '{"frozen":1}',
                            "analysis": '{"analysis":1}',
                        },
                    )
                ).scalar_one()
                await work.session.execute(
                    text(
                        "INSERT INTO evaluation_cases(user_id,history_entry_id,scope,request,"
                        "ai_verdict,human_verdict,ai_reasoning,accuracy,industry) "
                        "VALUES (:owner,:history,'scope','request','in_scope','in_scope',"
                        "'reason','correct','Development'), "
                        "(:owner,NULL,'scope','request','in_scope','in_scope','reason','correct','Development')"
                    ),
                    {"owner": owner, "history": old},
                )
                await work.session.execute(
                    text(
                        "INSERT INTO projects(user_id,name,industry,scope,created_at) "
                        "VALUES (:owner,'Legacy','Development','legacy','2000-01-01')"
                    ),
                    {"owner": owner},
                )
                await work.commit()
            data = (await call("GET", path)).json()["project"]
            # Real repository/use-case outputs are detached immutable values, not JSON aliases.
            service = ProjectService(lambda: ProjectUnitOfWork(app.state.database.new_uow()))
            immutable = await service.get(owner, identifier)
            assert isinstance(immutable.history, tuple)
            with pytest.raises(FrozenInstanceError):
                immutable.project.card.scope.text = "Changed"  # type: ignore[misc]
            with pytest.raises(FrozenInstanceError):
                immutable.history[0].summary = "Changed"  # type: ignore[misc]
            wire = project_to_wire(immutable)
            wire["scope"] = "Changed"
            wire["history"][0]["summary"] = "Changed"
            wire["history"].clear()
            assert project_to_wire(immutable) == data
            assert project_to_wire(await service.get(owner, identifier)) == data
            assert isinstance(await service.list(owner), tuple)
            async with ProjectUnitOfWork(app.state.database.new_uow()) as work:
                entities = await work.projects.list_owned(UUID(owner))
                entries = await work.history.for_projects((UUID(identifier),))
                assert isinstance(entities, tuple) and isinstance(entries, tuple)
                with pytest.raises(FrozenInstanceError):
                    entities[0].card.client.value = "Changed"  # type: ignore[misc]
                with pytest.raises(FrozenInstanceError):
                    entries[0].request = "Changed"  # type: ignore[misc]
            assert [entry["request"] for entry in data["history"]] == ["New", "Old"]
            assert data["history"][0]["draftId"] == str(draft)
            assert "draftId" not in data["history"][1] and "projectId" not in data["history"][0]
            listed = (await call("GET")).json()["projects"]
            assert [item["name"] for item in listed] == ["Website", "Legacy"]
            assert listed[1]["startDate"] is None and listed[1]["pricingModel"] is None
            assert (await call("GET", selected=foreign_cookie)).json() == {"projects": []}
            edited = {**CARD, "name": "Edited", "pricingModel": "fixed", "fixedPrice": "50.00"}
            del edited["clientName"]
            updated = await call("PATCH", path, edited)
            assert updated.status_code == 200
            assert updated.json()["project"]["clientName"] == "Owner"
            assert updated.json()["project"]["hourlyRate"] is None
            assert updated.json()["project"]["history"] == data["history"]
            changed_client = await call("PATCH", path, {**edited, "clientName": " Acme "})
            assert changed_client.json()["project"]["clientName"] == "Acme"
            assert (await call("PATCH", path, {**edited, "clientName": None})).json()["project"][
                "clientName"
            ] is None
            async with app.state.database.new_uow() as work:
                assert (
                    await work.session.execute(
                        text("SELECT project_snapshot,analysis_snapshot FROM drafts")
                    )
                ).one() == ({"frozen": 1}, {"analysis": 1})
            assert (await call("DELETE", path)).json() == {"ok": True}
            assert (await call("DELETE", path)).status_code == 404
            async with app.state.database.new_uow() as work:
                for table in ("history_entries", "drafts"):
                    assert (
                        await work.session.execute(text("SELECT count(*) FROM " + table))
                    ).scalar_one() == 0
                assert (
                    await work.session.execute(
                        text("SELECT count(*) FROM evaluation_cases WHERE history_entry_id IS NULL")
                    )
                ).scalar_one() == 1
                assert (
                    await work.session.execute(text("SELECT count(*) FROM projects"))
                ).scalar_one() == 1
            # Foreign origins are rejected before auth, parsing or writes.
            assert (
                await client.post(
                    "/api/projects", content="{", headers={"origin": "https://foreign.test"}
                )
            ).status_code == 403

    asyncio.run(run())
