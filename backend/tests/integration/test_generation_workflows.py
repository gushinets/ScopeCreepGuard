import asyncio
import json
from pathlib import Path

import httpx
import pytest
from integration.support import prepare_alembic
from pydantic import SecretStr
from scope_guard_api.main import create_app
from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.domain.analysis.normalization import parse_analysis, parse_materials

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("historical_auth")]
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


def test_retired_generation_never_calls_provider_or_mutates_legacy_data(disposable_url):
    prepare_alembic(disposable_url)

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
            for path in (
                "/api/analyze",
                "/api/replies/regenerate",
                "/api/client-materials/language",
                "/api/change-orders/estimate",
            ):
                for cookie in owners:
                    response = await call(path, body, cookie)
                    assert response.status_code == 503
                    assert response.json() == {"error": "errors.workflowUnavailable"}
            assert generator.calls == 0 and contexts == []
            assert before == await state()
            assert app.state.database.engine.pool.checkedout() == 0

    asyncio.run(run())
