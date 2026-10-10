import asyncio
import json
from pathlib import Path

import httpx
import pytest
from integration.support import replay_drizzle
from pydantic import SecretStr
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.main import create_app
from scope_guard.modules.analysis.normalization import parse_analysis, parse_materials

pytestmark = pytest.mark.integration
FIXTURE = json.loads(
    (Path(__file__).parents[3] / "contracts/compatibility/any-640/generation.json").read_text(
        encoding="utf-8"
    )
)
CARD = {
    "name": "Website",
    "industry": "Development",
    "scope": "Five pages only.",
    "startDate": "2026-01-01",
    "pricingModel": "hourly",
    "currency": "EUR",
    "hourlyRate": "100",
}


def test_generation_reads_are_owned_detached_and_never_write(disposable_url):
    replay_drizzle(disposable_url)

    async def run():
        app = create_app(
            Settings(
                _env_file=None,
                database_url=SecretStr(disposable_url),
                auth_secret=SecretStr("synthetic-generation-secret"),
            ),
            clock=lambda: 1791622800,
        )
        contexts = []

        class Generator:
            calls = 0

            async def close(self):
                pass

            async def analyze(self, value):
                assert app.state.database.engine.pool.checkedout() == 0
                contexts.append(value.context)
                self.calls += 1
                return parse_analysis(FIXTURE["analysisFixture"], value.locale)

            async def regenerate_reply(self, value):
                assert app.state.database.engine.pool.checkedout() == 0
                contexts.append(value.context)
                self.calls += 1
                return "reply"

            async def translate_materials(self, value):
                assert app.state.database.engine.pool.checkedout() == 0
                contexts.append(value.context)
                self.calls += 1
                co = FIXTURE["analysisFixture"]["changeOrder"]
                return parse_materials(
                    {
                        "clientLanguage": "en",
                        "replies": FIXTURE["analysisFixture"]["replies"],
                        "changeOrder": {
                            key: co[key]
                            for key in ("description", "timelineImpact", "rationale", "note")
                        },
                    },
                    "en",
                )

        generator = Generator()
        app.state.generator = generator
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            owners = []
            for email in ("owner@example.test", "other@example.test"):
                response = await client.post(
                    "/api/auth/register", json={"email": email, "password": "12345678"}
                )
                owners.append(response.headers["set-cookie"].split(";")[0] + "; locale=en")

            async def call(path, body, cookie=owners[0]):
                return await client.post(path, json=body, headers={"cookie": cookie})

            project = (await call("/api/projects", CARD)).json()["project"]
            body = {"projectId": project["id"], "request": "Add another page"}

            async def state():
                async with app.state.database.new_uow() as work:
                    return (
                        await work.session.execute(
                            text(
                                "SELECT (SELECT count(*) FROM history_entries), "
                                "(SELECT count(*) FROM drafts), "
                                "(SELECT count(*) FROM evaluation_cases), "
                                "(SELECT row_to_json(p)::text FROM projects p LIMIT 1)"
                            )
                        )
                    ).one()

            before = await state()
            analyzed = await call("/api/analyze", body)
            assert (
                analyzed.status_code == 200
                and analyzed.headers["cache-control"] == "private, no-store"
            )
            historical = {**body, "proof": analyzed.json()["proof"], "locale": "en"}
            for path, payload in (
                ("/api/replies/regenerate", {**body, "tone": "firm", "previousReply": "old"}),
                (
                    "/api/client-materials/language",
                    {**historical, "analysis": analyzed.json()["result"], "clientLanguage": "en"},
                ),
                ("/api/change-orders/estimate", historical),
            ):
                response = await call(path, payload)
                assert response.status_code == 200, response.text
                assert "cache-control" not in response.headers
                assert (await call(path, payload, owners[1])).status_code == 404
            assert generator.calls == 4 and before == await state()
            async with app.state.database.new_uow() as work:
                await work.session.execute(
                    text(
                        "UPDATE projects SET scope='new scope', name='New', "
                        "hourly_rate=999 WHERE id=:id"
                    ),
                    {"id": project["id"]},
                )
                await work.commit()
            assert (await call("/api/change-orders/estimate", historical)).status_code == 200
            assert contexts[-1].scope == "Five pages only." and contexts[-1].hourly_rate == "100.00"
            assert (
                await call(
                    "/api/replies/regenerate", {**body, "tone": "warm", "previousReply": "old"}
                )
            ).status_code == 200
            assert contexts[-1].scope == "new scope"
            assert (
                await call("/api/change-orders/estimate", {**historical, "draftId": None})
            ).json() == {"error": "errors.draftProofInvalid"}
            assert (
                await call("/api/analyze", {**body, "projectId": "malformed"})
            ).status_code == 500
            assert (await call("/api/analyze", body, owners[0] + "; locale=bad")).status_code == 500
            assert app.state.database.engine.pool.checkedout() == 0

    asyncio.run(run())
