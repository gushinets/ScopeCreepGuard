"""ANY-556 current Draft reads use disposable PostgreSQL, never app databases."""

import asyncio
import csv
import io
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from scope_guard_api.main import create_app
from sqlalchemy import create_engine, text

from scope_guard.core.config import Settings
from scope_guard.database.migrations import migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration
CARD = {
    "name": "Website",
    "industry": "Development",
    "scope": "Five agreed pages",
    "startDate": "2026-01-01",
    "pricingModel": "hourly",
    "currency": "EUR",
    "hourlyRate": "100",
}


def test_collection_filters_pages_exports_and_ownership(disposable_url, monkeypatch):
    engine = create_engine(normalize_url(disposable_url))
    with engine.begin() as connection:
        migrate(connection, target="head")
    failures = []
    monkeypatch.setattr("scope_guard_api.errors.log_unexpected", failures.append)

    async def exercise():
        app = create_app(
            Settings(
                _env_file=None,
                workflow_v2=True,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic-any556-at-least-32-characters"),
            )
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            cookies = []
            for index in range(2):
                result = await client.post(
                    "/api/auth/register",
                    json={
                        "email": f"draft-{index}@example.test",
                        "password": "12345678",
                    },
                )
                assert result.status_code == 201, result.text
                from uuid import UUID

                from scope_guard.database.repositories.users import AuthUnitOfWork
                from scope_guard.integrations.auth.passwords import Passwords
                from scope_guard.services.auth.tokens import AuthTokenService

                confirmation = AuthTokenService(
                    lambda: AuthUnitOfWork(app.state.database.new_uow()), Passwords()
                )
                owner_id = UUID(result.json()["user"]["id"])
                link = await confirmation.issue_pending_confirmation(owner_id)
                await confirmation.confirm_email(owner_id, link.raw)
                cookies.append(result.headers["set-cookie"].split(";")[0])

            async def call(path, *, method="GET", body=None, owner=0):
                return await client.request(
                    method, path, json=body, headers={"cookie": cookies[owner]}
                )

            projects, drafts = [], []
            for index in range(54):
                created = await call(
                    "/api/v2/projects",
                    method="POST",
                    body={
                        **CARD,
                        "name": f"Project {index}",
                        "operationId": str(uuid4()),
                    },
                )
                assert created.status_code == 201, (created.text, repr(failures))
                project = created.json()["project"]
                draft = (await call(f"/api/v2/projects/{project['id']}/draft")).json()["draft"]
                projects.append(project)
                drafts.append(draft)
            foreign = (
                await call(
                    "/api/v2/projects",
                    method="POST",
                    owner=1,
                    body={
                        **CARD,
                        "operationId": str(uuid4()),
                    },
                )
            ).json()["project"]
            foreign_draft = (await call(f"/api/v2/projects/{foreign['id']}/draft", owner=1)).json()[
                "draft"
            ]
            await call(f"/api/v2/projects/{projects[-1]['id']}", method="DELETE")
            with engine.begin() as connection:
                connection.execute(text("UPDATE drafts SET created_at='2026-10-20 12:00:00+00'"))
                for index, timestamp in (
                    (0, "2026-10-19 23:59:59+00"),
                    (1, "2026-10-20 00:00:00+00"),
                    (2, "2026-10-20 23:59:59.999999+00"),
                    (3, "2026-10-21 00:00:00+00"),
                ):
                    connection.execute(
                        text("UPDATE drafts SET created_at=:at WHERE id=:id"),
                        {"at": timestamp, "id": drafts[index]["id"]},
                    )
            first = await call("/api/v2/drafts")
            assert first.status_code == 200, first.text
            assert first.headers["cache-control"] == "private, no-store"
            value = first.json()
            assert value["total"] == 53 and value["hasDrafts"] is True
            assert len(value["drafts"]) == 50
            assert value["drafts"][0]["id"] == drafts[3]["id"]
            second = (await call("/api/v2/drafts?offset=50")).json()
            assert len(second["drafts"]) == 3
            newest = value["drafts"] + second["drafts"]
            oldest = (await call("/api/v2/drafts?sort=oldest&limit=100")).json()["drafts"]
            assert [d["id"] for d in oldest] == [d["id"] for d in newest][::-1]
            same_day = (
                await call("/api/v2/drafts?createdFrom=2026-10-20&createdTo=2026-10-20&limit=100")
            ).json()
            assert same_day["total"] == 51
            ids = {row["id"] for row in same_day["drafts"]}
            assert drafts[1]["id"] in ids and drafts[2]["id"] in ids
            assert drafts[0]["id"] not in ids and drafts[3]["id"] not in ids
            filtered = f"projectId={projects[1]['id']}&createdFrom=2026-10-20&createdTo=2026-10-20"
            assert (await call(f"/api/v2/drafts?{filtered}")).json()["total"] == 1
            assert (await call("/api/v2/drafts?createdFrom=2027-01-01")).json() == {
                "drafts": [],
                "total": 0,
                "hasDrafts": True,
            }
            for project_id in (foreign["id"], projects[-1]["id"], str(uuid4())):
                assert (await call(f"/api/v2/drafts?projectId={project_id}")).json() == {
                    "drafts": [],
                    "total": 0,
                    "hasDrafts": True,
                }
            for query in (
                "createdFrom=2026-02-30",
                "createdFrom=2026-10-21&createdTo=2026-10-20",
                "createdFrom=2026-10-20T00:00:00Z",
                "createdTo=9999-12-31",
                "projectId=bad",
                "sort=DROP",
                "limit=0",
                "limit=101",
                "offset=-1",
            ):
                assert (await call(f"/api/v2/drafts?{query}")).status_code == 400

            saved = (
                await call(
                    f"/api/v2/drafts/{drafts[1]['id']}",
                    method="PUT",
                    body={
                        "expectedRevision": "1",
                        "operationId": str(uuid4()),
                        "patch": {"requestText": 'Edited request\nUnicode Юникод, quotes "ok"'},
                    },
                )
            ).json()["draft"]

            def snapshot():
                with engine.connect() as connection:
                    tables = (
                        connection.execute(
                            text(
                                "SELECT tablename FROM pg_tables "
                                "WHERE schemaname='public' ORDER BY tablename"
                            )
                        )
                        .scalars()
                        .all()
                    )
                    return {
                        name: connection.execute(
                            text(
                                'SELECT to_jsonb(t)::text FROM "'
                                + name
                                + '" t ORDER BY to_jsonb(t)::text'
                            )
                        )
                        .scalars()
                        .all()
                        for name in tables
                    }

            before = snapshot()
            for locale, delimiter in (("en", ","), ("ru", ";")):
                response = await call(f"/api/v2/drafts/export.csv?locale={locale}")
                assert response.status_code == 200, response.text
                assert response.content.startswith(b"\xef\xbb\xbf")
                assert response.headers["cache-control"] == "private, no-store"
                assert response.headers["content-type"] == "text/csv; charset=utf-8"
                assert "attachment;" in response.headers["content-disposition"]
                rows = list(
                    csv.reader(
                        io.StringIO(response.content.decode("utf-8-sig")), delimiter=delimiter
                    )
                )
                assert len(rows) == 54
                assert [row[0] for row in rows[1:]] == [d["id"] for d in newest]
                selected = await call(
                    f"/api/v2/drafts/{saved['id']}/export.csv?locale={locale}&expectedRevision={saved['revision']}"
                )
                single = list(
                    csv.reader(
                        io.StringIO(selected.content.decode("utf-8-sig")), delimiter=delimiter
                    )
                )
                assert len(single) == 2 and single[1][6] == saved["requestText"]
                assert single[1][5] == saved["revision"] and single[1][7] == ""
                empty = await call(
                    f"/api/v2/drafts/export.csv?locale={locale}&createdFrom=2027-01-01"
                )
                assert (
                    len(
                        list(
                            csv.reader(
                                io.StringIO(empty.content.decode("utf-8-sig")), delimiter=delimiter
                            )
                        )
                    )
                    == 1
                )
                equivalent = await call(f"/api/v2/drafts/export.csv?{filtered}&locale={locale}")
                assert (
                    len(
                        list(
                            csv.reader(
                                io.StringIO(equivalent.content.decode("utf-8-sig")),
                                delimiter=delimiter,
                            )
                        )
                    )
                    == 2
                )
            for identifier in (foreign_draft["id"], drafts[-1]["id"], str(uuid4())):
                result = await call(f"/api/v2/drafts/{identifier}/export.csv")
                assert result.status_code == 404
                assert result.json() == {"error": "errors.draftNotFound"}
            assert (
                await call(f"/api/v2/drafts/{saved['id']}/export.csv?expectedRevision=1")
            ).status_code == 409
            assert snapshot() == before

    try:
        asyncio.run(exercise())
    finally:
        engine.dispose()
