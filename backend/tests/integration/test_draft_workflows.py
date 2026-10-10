import asyncio
import copy
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from integration.support import replay_drizzle
from pydantic import SecretStr
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
from scope_guard.main import create_app
from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
from scope_guard.modules.analysis.normalization import parse_snapshot

pytestmark = pytest.mark.integration
FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())
CARD = {
    "name": "Website",
    "industry": "Development",
    "scope": "Five pages",
    "startDate": "2026-01-01",
    "pricingModel": "hourly",
    "currency": "EUR",
    "hourlyRate": "100",
}
SECRET = "synthetic-draft-secret-at-least-32-characters"


def test_draft_owner_concurrency_retry_updates_and_legacy(disposable_url, monkeypatch):
    replay_drizzle(disposable_url)

    async def run():
        clock = [1791622800.123]
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr(SECRET),
            ),
            clock=lambda: clock[0],
        )

        class NoLLM:
            async def close(self):
                pass

            async def analyze(self, _):
                pytest.fail("Drafts must never call LLM")

            regenerate_reply = translate_materials = analyze

        app.state.generator = NoLLM()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            cookies, users = [], []
            for email in ("owner@example.test", "other@example.test"):
                response = await client.post(
                    "/api/auth/register", json={"email": email, "password": "12345678"}
                )
                users.append(response.json()["user"]["id"])
                cookies.append(response.headers["set-cookie"].split(";")[0])

            async def call(method, path, body=None, owner=0):
                return await client.request(
                    method, path, json=body, headers={"cookie": cookies[owner]}
                )

            project = (await call("POST", "/api/projects", CARD)).json()["project"]
            claims = DraftProofClaims(
                DraftProofBinding(users[0], project["id"], "Add another page", "en"),
                parse_snapshot(FIXTURE["analysis"], "en"),
                freeze(FIXTURE["snapshot"]),
            )
            proof = DraftProofs(SECRET, lambda: clock[0]).issue(claims)
            body = {
                "projectId": project["id"],
                "request": "Add another page",
                "locale": "en",
                "idempotencyKey": str(uuid4()),
                "proof": proof,
                "draftDocument": FIXTURE["document"],
            }
            responses = await asyncio.gather(*(call("POST", "/api/drafts", body) for _ in range(2)))
            assert sorted(r.status_code for r in responses) == [200, 201]
            assert responses[0].json() == responses[1].json()
            saved = responses[0].json()
            draft = saved["draft"]
            assert saved["entry"]["projectId"] == project["id"]
            assert saved["entry"]["draftId"] == draft["id"]
            assert draft["createdAt"] == "2026-10-10T09:00:00.123Z"
            path = "/api/drafts/" + draft["id"]
            changed = copy.deepcopy(body)
            changed["draftDocument"]["reply"]["text"] = "Retry edited"
            response = await call("POST", "/api/drafts", changed)
            assert response.status_code == 200 and response.json() == saved
            for identifier in (draft["id"], str(uuid4()), "malformed", "{" + draft["id"] + "}"):
                for method in ("GET", "PUT"):
                    r = await call(
                        method, "/api/drafts/" + identifier, {"draftDocument": {}}, owner=1
                    )
                    assert r.status_code == 404 and r.json() == {"error": "errors.draftNotFound"}
                    if method == "GET":
                        assert r.headers["cache-control"] == "private, no-store"
            assert (await call("GET", "/api/drafts", owner=1)).json() == {"drafts": []}
            assert (await call("POST", "/api/drafts", body, owner=1)).json() == {
                "error": "errors.draftProofInvalid"
            }
            async with app.state.database.engine.connect() as connection:
                before_history = (
                    (await connection.execute(text("SELECT * FROM history_entries")))
                    .mappings()
                    .all()
                )
                before_project = (
                    (await connection.execute(text("SELECT * FROM projects"))).mappings().all()
                )
            clock[0] += 1
            r = await call(
                "PUT",
                path,
                {
                    "draftDocument": changed["draftDocument"],
                    "analysisSnapshot": {},
                    "projectSnapshot": {},
                },
            )
            assert r.status_code == 200
            updated = r.json()["draft"]
            for field in (
                "projectSnapshot",
                "analysisSnapshot",
                "request",
                "locale",
                "requestLanguage",
                "createdAt",
                "historyEntryId",
            ):
                assert updated[field] == draft[field]
            assert updated["draftDocument"] == changed["draftDocument"]
            assert updated["updatedAt"] != draft["updatedAt"]
            async with app.state.database.engine.begin() as connection:
                await connection.execute(
                    text(
                        "CREATE FUNCTION fail_edit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                        "BEGIN RAISE EXCEPTION 'injected'; END $$"
                    )
                )
                await connection.execute(
                    text(
                        "CREATE TRIGGER fail_edit BEFORE UPDATE ON drafts "
                        "FOR EACH ROW EXECUTE FUNCTION fail_edit()"
                    )
                )
            r = await call("PUT", path, {"draftDocument": FIXTURE["document"]})
            assert r.status_code == 500 and r.json() == {"error": "errors.draftSaveFailed"}
            assert (await call("GET", path)).json()["draft"] == updated
            async with app.state.database.engine.begin() as connection:
                await connection.execute(text("DROP TRIGGER fail_edit ON drafts"))
                await connection.execute(text("DROP FUNCTION fail_edit()"))
            # Cancel after history/draft flush, before project update or commit.
            from scope_guard.infrastructure.database.repositories.draft_persistence import (
                DraftRepository,
            )

            entered = asyncio.Event()

            async def pause_before_project_update(*_):
                entered.set()
                await asyncio.Event().wait()

            with monkeypatch.context() as patch:
                patch.setattr(DraftRepository, "mark_checked", pause_before_project_update)
                pending = asyncio.create_task(
                    call("POST", "/api/drafts", {**body, "idempotencyKey": str(uuid4())})
                )
                await asyncio.wait_for(entered.wait(), 5)
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await pending
            async with app.state.database.engine.begin() as connection:
                assert (
                    await connection.execute(text("SELECT * FROM history_entries"))
                ).mappings().all() == before_history
                assert (
                    await connection.execute(text("SELECT * FROM projects"))
                ).mappings().all() == before_project
                assert (await connection.execute(text("SELECT count(*) FROM drafts"))).scalar() == 1
                await connection.execute(text("UPDATE drafts SET project_snapshot=NULL"))
            assert (await call("GET", path)).json()["draft"]["projectSnapshot"] is None
            assert (await call("PUT", path, {"draftDocument": changed["draftDocument"]})).json()[
                "draft"
            ]["projectSnapshot"] is None
            # Equal created times must sort by UUID descending; empty snapshot name wins COALESCE.
            body["idempotencyKey"] = str(uuid4())
            await call("POST", "/api/drafts", body)
            async with app.state.database.engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE drafts SET created_at='2026-10-10T09:00:00Z', "
                        "project_snapshot=jsonb_build_object('name','')"
                    )
                )
            listing = await call("GET", "/api/drafts")
            items = listing.json()["drafts"]
            assert [i["id"] for i in items] == sorted([i["id"] for i in items], reverse=True)
            assert all(i["projectName"] == "" for i in items)
            assert listing.headers["cache-control"] == "private, no-store"
            clock[0] += 3600
            assert (await call("POST", "/api/drafts", body)).json() == {
                "error": "errors.draftProofInvalid"
            }
            assert app.state.database.engine.pool.checkedout() == 0

    asyncio.run(run())


@pytest.mark.parametrize("table", ["drafts", "projects", "commit"])
def test_draft_transaction_rolls_back_injected_database_failure(disposable_url, table):
    replay_drizzle(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr(SECRET),
            ),
            clock=lambda: 1791622800,
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            user = (
                await client.post(
                    "/api/auth/register",
                    json={"email": "owner@example.test", "password": "12345678"},
                )
            ).json()["user"]
            project = (await client.post("/api/projects", json=CARD)).json()["project"]
            proof = DraftProofs(SECRET, lambda: 1791622800).issue(
                DraftProofClaims(
                    DraftProofBinding(user["id"], project["id"], "Add another page", "en"),
                    parse_snapshot(FIXTURE["analysis"], "en"),
                    freeze(FIXTURE["snapshot"]),
                )
            )
            async with app.state.database.engine.begin() as connection:
                await connection.execute(
                    text(
                        "CREATE FUNCTION fail_save() RETURNS trigger LANGUAGE plpgsql AS $$ "
                        "BEGIN RAISE EXCEPTION 'injected'; END $$"
                    )
                )
                if table == "commit":
                    sql = (
                        "CREATE CONSTRAINT TRIGGER fail_save AFTER UPDATE ON projects "
                        "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fail_save()"
                    )
                else:
                    operation = "INSERT" if table == "drafts" else "UPDATE"
                    sql = (
                        f"CREATE TRIGGER fail_save BEFORE {operation} ON {table} "
                        "FOR EACH ROW EXECUTE FUNCTION fail_save()"
                    )
                await connection.execute(text(sql))
            response = await client.post(
                "/api/drafts",
                json={
                    "projectId": project["id"],
                    "request": "Add another page",
                    "locale": "en",
                    "idempotencyKey": str(uuid4()),
                    "proof": proof,
                    "draftDocument": FIXTURE["document"],
                },
            )
            assert response.status_code == 500 and response.json() == {
                "error": "errors.draftSaveFailed"
            }
            async with app.state.database.engine.connect() as connection:
                for name in ("history_entries", "drafts"):
                    assert (
                        await connection.execute(text(f"SELECT count(*) FROM {name}"))
                    ).scalar() == 0
                assert (
                    await connection.execute(text("SELECT last_checked FROM projects"))
                ).scalar() is None

    asyncio.run(run())
