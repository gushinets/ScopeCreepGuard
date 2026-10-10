"""Test-only HTTP application with the frozen compatibility clock."""

import json
import os
import time
from pathlib import Path

from scope_guard.core.config import Settings
from scope_guard.main import create_app

app = create_app(
    Settings(_env_file=None),
    clock=time.time if os.environ.get("SCG_AUTH_REALTIME") == "1" else lambda: 1791622800,
)


class FixtureGenerator:
    """Deterministic provider port in this test entrypoint only; never in production."""

    calls = 0

    def __init__(self):
        self.fixture = json.loads(
            (
                Path(__file__).parents[2] / "contracts/compatibility/any-640/generation.json"
            ).read_text(encoding="utf-8")
        )

    async def close(self):
        pass

    async def analyze(self, value):
        from scope_guard.modules.analysis.normalization import parse_analysis

        self.calls += 1
        return parse_analysis(self.fixture["analysisFixture"], value.locale)

    async def regenerate_reply(self, value):
        self.calls += 1
        return self.fixture["analysisFixture"]["replies"][value.tone]

    async def translate_materials(self, value):
        from scope_guard.modules.analysis.normalization import parse_materials

        self.calls += 1
        co = self.fixture["analysisFixture"]["changeOrder"]
        return parse_materials(
            {
                "clientLanguage": value.client_language,
                "replies": self.fixture["analysisFixture"]["replies"],
                "changeOrder": {
                    key: co[key] for key in ("description", "timelineImpact", "rationale", "note")
                },
            },
            value.client_language,
        )


app.state.generator = FixtureGenerator()


@app.get("/__generation_calls", include_in_schema=False)
async def generation_calls():
    return {"calls": app.state.generator.calls}


if __name__ == "__main__":
    import sys

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(sys.argv[1]),
        loop="scope_guard.infrastructure.database.session:event_loop",
    )
