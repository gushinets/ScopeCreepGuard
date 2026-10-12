import asyncio

import httpx
import pytest
from integration.support import prepare_alembic
from pydantic import SecretStr
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard_api.main import create_app

pytestmark = pytest.mark.integration
SECRET = "slice-f-secret-at-least-32-characters"
CARD = {
    "name": "Website",
    "industry": "Development",
    "scope": "Five pages",
    "startDate": "2026-01-01",
    "pricingModel": "hourly",
    "currency": "EUR",
    "hourlyRate": "100",
}


def test_history_evaluation_export_and_owner_isolation(disposable_url):
    prepare_alembic(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr(SECRET),
            ),
            clock=lambda: 1791622800.0,
        )

        class NoLLM:
            async def close(self):
                pass

            async def analyze(self, _):
                pytest.fail("remaining operations must never call an LLM")

            regenerate_reply = translate_materials = analyze

        app.state.generator = NoLLM()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            cookies = []
            users = []
            for email in ("owner@example.test", "other@example.test"):
                response = await client.post(
                    "/api/auth/register", json={"email": email, "password": "12345678"}
                )
                cookies.append(response.headers["set-cookie"].split(";")[0])
                users.append(response.json()["user"]["id"])

            async def call(method, path, body=None, owner=0, raw=None):
                return await client.request(
                    method,
                    path,
                    json=body if raw is None else None,
                    content=raw,
                    headers={"cookie": cookies[owner]},
                )

            project = (await call("POST", "/api/projects", CARD)).json()["project"]
            path = f"/api/projects/{project['id']}/history"
            assert (await call("POST", path, owner=1, raw="[")).status_code == 404
            assert (await call("POST", path, raw="[")).json() == {
                "error": "errors.requestBodyInvalid"
            }
            cases = [
                ({}, "errors.historyDateInvalid"),
                ({"date": "2026/10/10"}, "errors.historyDateInvalid"),
                ({"date": "2026-10-10", "request": " "}, "errors.requestRequired"),
                (
                    {"date": "2026-10-10", "request": "x", "verdict": "bad"},
                    "errors.verdictInvalid",
                ),
                (
                    {
                        "date": "2026-10-10",
                        "request": "x",
                        "verdict": "in_scope",
                        "summary": " ",
                    },
                    "errors.summaryRequired",
                ),
            ]
            for body, error in cases:
                response = await call("POST", path, body)
                assert response.status_code == 400 and response.json() == {"error": error}

            created = await call(
                "POST",
                path,
                {
                    "date": "2026-10-10",
                    "request": "  Добавить страницу  ",
                    "verdict": "out_of_scope",
                    "summary": "  Новая работа  ",
                },
            )
            assert created.status_code == 201
            entry = created.json()["entry"]
            assert entry == {
                "id": entry["id"],
                "date": "2026-10-10",
                "request": "Добавить страницу",
                "verdict": "out_of_scope",
                "summary": "Новая работа",
            }
            reloaded = (await call("GET", f"/api/projects/{project['id']}")).json()["project"]
            assert reloaded["lastChecked"] == "2026-10-10"
            assert reloaded["history"][0] == entry

            malformed = await call(
                "POST",
                "/api/evaluations",
                {"historyEntryId": "bad", "accuracy": "correct", "aiReasoning": "why"},
            )
            assert malformed.status_code == 404
            assert malformed.json() == {"error": "errors.evaluationHistoryNotFound"}
            missing = await call(
                "POST",
                "/api/evaluations",
                {
                    "historyEntryId": "10000000-0000-4000-8000-000000000000",
                    "accuracy": "correct",
                    "aiReasoning": "why",
                },
            )
            assert missing.status_code == malformed.status_code
            assert missing.json() == malformed.json()
            assert (
                await call(
                    "POST",
                    "/api/evaluations",
                    {
                        "historyEntryId": entry["id"],
                        "accuracy": "wrong",
                        "humanVerdict": "out_of_scope",
                        "aiReasoning": "why",
                    },
                )
            ).json() == {"error": "errors.evaluationLabelInvalid"}
            foreign = await call(
                "POST",
                "/api/evaluations",
                {"historyEntryId": entry["id"], "accuracy": "correct", "aiReasoning": "why"},
                owner=1,
            )
            assert foreign.status_code == 404
            assert foreign.json() == {"error": "errors.evaluationHistoryNotFound"}

            first = await call(
                "POST",
                "/api/evaluations",
                {
                    "historyEntryId": entry["id"],
                    "accuracy": "correct",
                    "aiReasoning": "  Это новая работа  ",
                },
            )
            assert first.status_code == 200
            evaluation = first.json()["evaluation"]
            assert evaluation["humanVerdict"] == "out_of_scope"

            changed = {**CARD, "scope": "Ten pages", "industry": "Marketing"}
            updated = await call("PATCH", f"/api/projects/{project['id']}", changed)
            assert updated.status_code == 200
            second = await call(
                "POST",
                "/api/evaluations",
                {
                    "historyEntryId": entry["id"],
                    "accuracy": "debatable",
                    "aiReasoning": "  Спорно  ",
                },
            )
            assert second.status_code == 200
            assert second.json()["evaluation"] == {
                "id": evaluation["id"],
                "accuracy": "debatable",
                "humanVerdict": None,
            }

            concurrent = await asyncio.gather(
                call(
                    "POST",
                    "/api/evaluations",
                    {
                        "historyEntryId": entry["id"],
                        "accuracy": "correct",
                        "aiReasoning": "Concurrent correct",
                    },
                ),
                call(
                    "POST",
                    "/api/evaluations",
                    {
                        "historyEntryId": entry["id"],
                        "accuracy": "debatable",
                        "aiReasoning": "Concurrent debatable",
                    },
                ),
            )
            assert [response.status_code for response in concurrent] == [200, 200]

            async with app.state.database.new_uow() as work:
                await work.session.execute(
                    text(
                        "INSERT INTO evaluation_cases "
                        "(user_id,history_entry_id,scope,request,ai_verdict,human_verdict,"
                        "ai_reasoning,accuracy,industry,created_at,updated_at) VALUES "
                        "(:owner,NULL,'Legacy scope','Legacy request','in_scope','in_scope',"
                        "'Legacy reasoning','correct','Design','2000-01-01','2000-01-01')"
                    ),
                    {"owner": users[0]},
                )
                await work.commit()

            exported = await call("GET", "/api/evaluations/export")
            assert exported.status_code == 200
            assert exported.headers["content-type"] == "application/x-ndjson; charset=utf-8"
            assert exported.headers["content-disposition"] == (
                'attachment; filename="scope-creep-evaluations.jsonl"'
            )
            lines = exported.content.decode().splitlines()
            assert lines[0] == (
                '{"scope":"Legacy scope","request":"Legacy request",'
                '"ai_verdict":"IN_SCOPE","human_verdict":"IN_SCOPE",'
                '"ai_reasoning":"Legacy reasoning","project_type":"design"}'
            )
            assert len(lines) == 2 and exported.content.endswith(b"\n")
            assert '"scope":"Ten pages"' in lines[1]
            assert '"request":"Добавить страницу"' in lines[1]
            assert '"ai_verdict":"OUT_OF_SCOPE"' in lines[1]
            assert '"project_type":"marketing"' in lines[1]
            empty = await call("GET", "/api/evaluations/export", owner=1)
            assert empty.status_code == 200 and empty.content == b""

            async with app.state.database.new_uow() as work:
                counts = (
                    await work.session.execute(
                        text(
                            "SELECT (SELECT count(*) FROM history_entries),"
                            "(SELECT count(*) FROM evaluation_cases),"
                            "(SELECT count(*) FROM drafts)"
                        )
                    )
                ).one()
                assert tuple(counts) == (1, 2, 0)
                await work.rollback()

    asyncio.run(run())


def test_manual_history_rolls_back_insert_and_last_checked_when_commit_fails(
    disposable_url, monkeypatch
):
    prepare_alembic(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr(SECRET),
            )
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            registered = await client.post(
                "/api/auth/register",
                json={"email": "rollback@example.test", "password": "12345678"},
            )
            cookie = registered.headers["set-cookie"].split(";")[0]
            project = await client.post("/api/projects", json=CARD, headers={"cookie": cookie})
            project_id = project.json()["project"]["id"]

            from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork

            async def fail_commit(_self):
                raise RuntimeError("injected_commit_failure")

            with monkeypatch.context() as scoped:
                scoped.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
                response = await client.post(
                    f"/api/projects/{project_id}/history",
                    json={
                        "date": "2026-10-10",
                        "request": "Add a page",
                        "verdict": "out_of_scope",
                        "summary": "Extra work",
                    },
                    headers={"cookie": cookie},
                )
            assert response.status_code == 500
            assert response.json() == {"error": "errors.requestFailed"}

            async with app.state.database.new_uow() as work:
                state = (
                    await work.session.execute(
                        text(
                            "SELECT p.last_checked, count(h.id) FROM projects p "
                            "LEFT JOIN history_entries h ON h.project_id=p.id "
                            "WHERE p.id=:id GROUP BY p.last_checked"
                        ),
                        {"id": project_id},
                    )
                ).one()
                assert state == (None, 0)
                await work.rollback()

    asyncio.run(run())
