import asyncio
import copy
import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from integration.support import prepare_alembic
from pydantic import SecretStr
from pypdf import PdfReader
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
from scope_guard.main import create_app
from scope_guard.domain.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
from scope_guard.domain.analysis.normalization import parse_snapshot

pytestmark = pytest.mark.integration
FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())
SECRET = "synthetic-pdf-secret-at-least-32-characters"


def test_pdf_download_is_owned_historical_and_read_only(disposable_url, monkeypatch):
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
            cookies, users = [], []
            for address in ("owner@pdf.test", "foreign@pdf.test"):
                response = await client.post(
                    "/api/auth/register", json={"email": address, "password": "12345678"}
                )
                cookies.append(response.headers["set-cookie"].split(";")[0])
                users.append(response.json()["user"]["id"])

            async def call(method, path, body=None, owner=0):
                return await client.request(
                    method, path, json=body, headers={"cookie": cookies[owner]}
                )

            card = {
                "name": "Historical",
                "industry": "Development",
                "scope": "Five pages",
                "startDate": "2026-01-01",
                "pricingModel": "hourly",
                "currency": "EUR",
                "hourlyRate": "100",
            }
            project = (await call("POST", "/api/projects", card)).json()["project"]
            claims = DraftProofClaims(
                DraftProofBinding(users[0], project["id"], "Extra page", "en"),
                parse_snapshot(FIXTURE["analysis"], "en"),
                freeze(FIXTURE["snapshot"]),
            )
            document = copy.deepcopy(FIXTURE["document"])
            document["changeOrder"].update(
                description="My saved description",
                additionalCost="2.675",
                projectName="Historical Website",
            )
            body = {
                "projectId": project["id"],
                "request": "Extra page",
                "locale": "en",
                "idempotencyKey": str(uuid4()),
                "proof": DraftProofs(SECRET, app.state.clock).issue(claims),
                "draftDocument": document,
            }
            response = await call("POST", "/api/drafts", body)
            assert response.status_code == 201, response.text
            draft = response.json()["draft"]
            path = f"/api/drafts/{draft['id']}/pdf"
            assert (
                await call(
                    "PATCH",
                    f"/api/projects/{project['id']}",
                    {**card, "name": "TODAY TERMS", "currency": "USD", "hourlyRate": "900"},
                )
            ).status_code == 200

            def forbidden(*args, **kwargs):
                pytest.fail("Export must not generate or verify a proof")

            monkeypatch.setattr(DraftProofs, "verify", forbidden)
            monkeypatch.setattr(app.state.generator, "analyze", forbidden)
            monkeypatch.setattr(app.state.generator, "translate_materials", forbidden)

            async def rows():
                async with app.state.database.engine.connect() as connection:
                    return {
                        table: (await connection.execute(text(f"SELECT * FROM {table}")))
                        .mappings()
                        .all()
                        for table in ("drafts", "history_entries", "projects")
                    }

            before = await rows()
            for _ in range(2):
                response = await call("GET", path)
                assert response.status_code == 200, response.text
                assert response.headers["content-type"] == "application/pdf"
                assert response.headers["cache-control"] == "private, no-store"
                assert (
                    response.headers["content-disposition"]
                    == f'attachment; filename="change-order-{draft["id"]}.pdf"'
                )
                content = " ".join(
                    page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
                )
                assert "My saved description" in content and "2.675 EUR" in content
                assert "TODAY TERMS" not in content and "900" not in content
            assert await rows() == before
            for key in (draft["id"], str(uuid4()), "malformed"):
                response = await call("GET", f"/api/drafts/{key}/pdf", owner=1)
                assert response.status_code == 404 and response.json() == {
                    "error": "errors.draftNotFound"
                }
                assert response.headers["cache-control"] == "private, no-store"
            client.cookies.clear()
            assert (await client.get(path)).status_code == 401
            preview = {
                "projectId": project["id"],
                "draftId": draft["id"],
                "changeOrder": {**document["changeOrder"], "additionalCost": "9.995"},
            }
            response = await call("POST", "/api/change-orders/pdf", preview)
            assert response.status_code == 200
            assert "9.995 EUR" in " ".join(
                page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
            )
            assert await rows() == before
            assert (
                await call("POST", "/api/change-orders/pdf", preview, owner=1)
            ).status_code == 404
            # Legacy missing snapshots cannot introduce today's terms.
            async with app.state.database.engine.begin() as connection:
                await connection.execute(
                    text("UPDATE drafts SET project_snapshot = NULL WHERE id = :id"),
                    {"id": draft["id"]},
                )
            response = await call("GET", path)
            assert response.status_code == 200
            assert "TODAY TERMS" not in " ".join(
                page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
            )
            async with app.state.database.engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE drafts SET draft_document = "
                        "jsonb_set(draft_document, '{changeOrder}', 'null') WHERE id = :id"
                    ),
                    {"id": draft["id"]},
                )
            response = await call("GET", path)
            assert response.status_code == 400 and response.json() == {
                "error": "errors.pdfDocumentMissing"
            }

    asyncio.run(run())
