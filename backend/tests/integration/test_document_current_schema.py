import asyncio
from datetime import date
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
from integration.support import prepare_alembic
from pydantic import SecretStr
from pypdf import PdfReader
from scope_guard_api.main import create_app
from service_fixtures import editor
from sqlalchemy import event, insert, select, text

from scope_guard.core.config import Settings
from scope_guard.database.models.workflow import WORKFLOW_METADATA, drafts, projects

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("workflow_v2", [True, False])
def test_current_preview_references(disposable_url, workflow_v2):
    prepare_alembic(disposable_url, target="head")

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic-preview-secret"),
                workflow_v2=workflow_v2,
            )
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/register",
                    json={"email": "preview@example.test", "password": "synthetic-password"},
                )
                assert response.status_code == 201, response.text
                owner = UUID(response.json()["user"]["id"])
                async with app.state.database.engine.begin() as conn:
                    await conn.execute(
                        text("UPDATE users SET email_verified_at=now() WHERE id=:id"), {"id": owner}
                    )
                    project = (
                        await conn.execute(
                            insert(projects)
                            .values(
                                updated_at=text("now()"),
                                user_id=owner,
                                name="Preview project",
                                industry="Development",
                                scope="Scope",
                                start_date=date(2026, 1, 1),
                                pricing_model="hourly",
                                currency="EUR",
                                hourly_rate=100,
                            )
                            .returning(projects.c.id)
                        )
                    ).scalar_one()
                    draft = (
                        await conn.execute(
                            insert(drafts)
                            .values(
                                updated_at=text("now()"),
                                project_id=project,
                                request_text="Extra page",
                                draft_document={
                                    "reply": {"text": "", "language": "en"},
                                    "changeOrder": None,
                                },
                                revision=1,
                                analysis_is_stale=True,
                            )
                            .returning(drafts.c.id)
                        )
                    ).scalar_one()

                async with app.state.database.engine.begin() as conn:
                    foreign = (
                        await conn.execute(
                            insert(WORKFLOW_METADATA.tables["users"])
                            .values(email="foreign@example.test", password_hash="synthetic-hash")
                            .returning(WORKFLOW_METADATA.tables["users"].c.id)
                        )
                    ).scalar_one()
                    references = []
                    for project_owner in (owner, foreign):
                        another_project = (
                            await conn.execute(
                                insert(projects)
                                .values(
                                    updated_at=text("now()"),
                                    user_id=project_owner,
                                    name="Another",
                                    start_date=date(2026, 1, 1),
                                    industry="Development",
                                    scope="Private scope",
                                    pricing_model="hourly",
                                    currency="EUR",
                                    hourly_rate=100,
                                )
                                .returning(projects.c.id)
                            )
                        ).scalar_one()
                        another_draft = (
                            await conn.execute(
                                insert(drafts)
                                .values(
                                    updated_at=text("now()"),
                                    project_id=another_project,
                                    request_text="Private",
                                    draft_document={
                                        "reply": {"text": "", "language": "en"},
                                        "changeOrder": None,
                                    },
                                    revision=1,
                                    analysis_is_stale=True,
                                )
                                .returning(drafts.c.id)
                            )
                        ).scalar_one()
                        references.append(another_draft)

                async def state():
                    async with app.state.database.engine.connect() as conn:
                        return [
                            (await conn.execute(select(t))).all()
                            for t in WORKFLOW_METADATA.sorted_tables
                        ]

                path = "/api/v2/change-orders/pdf" if workflow_v2 else "/api/change-orders/pdf"
                other = "/api/change-orders/pdf" if workflow_v2 else "/api/v2/change-orders/pdf"
                assert (await client.post(other, json={})).status_code == (
                    426 if workflow_v2 else 503
                )
                before = await state()
                statements = []

                def observe(conn, cursor, statement, parameters, context, executemany):
                    statements.append(statement)

                event.listen(
                    app.state.database.engine.sync_engine, "before_cursor_execute", observe
                )
                for reference in (draft, uuid4(), *references):
                    response = await client.post(
                        path,
                        json={
                            "projectId": str(project),
                            "draftId": str(reference),
                            "changeOrder": editor(),
                        },
                    )
                    assert response.status_code == 404, response.text
                    assert response.json() == {"error": "errors.draftNotFound"}
                for bad in ("malformed", ""):
                    response = await client.post(
                        path,
                        json={"projectId": str(project), "draftId": bad, "changeOrder": editor()},
                    )
                    assert response.status_code == 404
                    assert response.json() == {"error": "errors.draftNotFound"}
                response = await client.post(
                    path, json={"projectId": str(uuid4()), "changeOrder": editor()}
                )
                assert response.status_code == 404
                assert response.json() == {"error": "errors.projectNotFound"}
                response = await client.post(
                    path, json={"projectId": str(another_project), "changeOrder": editor()}
                )
                assert response.status_code == 404
                assert response.json() == {"error": "errors.projectNotFound"}
                response = await client.post(
                    path, json={"projectId": "malformed", "changeOrder": editor()}
                )
                assert response.status_code == 400
                assert response.json() == {"error": "errors.requestBodyInvalid"}
                assert not any("drafts.history_entry_id" in s for s in statements)
                for language in ("ru", "en"):
                    response = await client.post(
                        path,
                        json={"projectId": str(project), "changeOrder": editor(language=language)},
                    )
                    assert response.status_code == 200, response.text
                    assert response.headers["content-type"] == "application/pdf"
                    content = " ".join(
                        p.extract_text() for p in PdfReader(BytesIO(response.content)).pages
                    )
                    assert editor()["description"] in content
                assert await state() == before

    asyncio.run(run())
