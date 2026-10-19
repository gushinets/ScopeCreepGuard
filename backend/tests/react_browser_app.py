"""Owned PostgreSQL + actual API/worker with deterministic provider responses.

This executable test entrypoint accepts only a port and a private state path.
It never loads application env files or a provider key.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from fastapi import Request
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from starlette.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))
from integration.support import DisposablePostgres, docker
from integration.test_llm_pipeline import output
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings
from scope_guard.database.migrations import migrate
from scope_guard.database.repositories.llm import LlmSQLStore
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import normalize_url
from scope_guard.domain.llm.runtime import ProviderResponse
from scope_guard.integrations.llm.gateway import ProviderGateway
from scope_guard.integrations.llm.stages import StructuredStageRunner, translation_commercial_terms
from scope_guard.integrations.storage.filesystem import FilesystemObjectStorage
from scope_guard.services.documents.export_worker import ExportWorker
from scope_guard.services.documents.rendering import DocumentRendering
from scope_guard.services.llm.worker import LlmWorker


@contextmanager
def fixture_database(state_file, resume):
    if not resume:
        with DisposablePostgres() as postgres, postgres.database() as url:
            yield url
        return
    saved = json.loads(state_file.read_text(encoding="utf-8"))
    parsed = urlsplit(saved["databaseUrl"])
    assert saved["disposableOnly"] and parsed.hostname == "127.0.0.1"
    assert parsed.username == "scg_test" and parsed.path.startswith("/scg_test_")
    candidates = json.loads(
        docker("inspect", *docker("ps", "-q", "--filter", "label=scope-guard.disposable").split())
    )
    owned = [
        item
        for item in candidates
        if item["Config"]["Labels"].get("scope-guard.disposable") == parsed.password
        and item["Name"].startswith("/scg-any639-test-")
        and any(
            int(binding["HostPort"]) == parsed.port
            for binding in item["NetworkSettings"]["Ports"].get("5432/tcp", [])
        )
    ]
    assert len(owned) == 1, "Resume requires the exact owned disposable database container"
    identifier = owned[0]["Id"]
    try:
        yield saved["databaseUrl"]
    finally:
        assert (
            docker(
                "inspect",
                "--format",
                '{{index .Config.Labels "scope-guard.disposable"}}',
                identifier,
            )
            == parsed.password
        )
        docker("rm", "-f", identifier)


def main():
    # This fixture must never inherit deployment secrets or application storage.
    for name in list(os.environ):
        if name.startswith(("SCOPE_GUARD_", "SCG_", "PG")) or name in (
            "DATABASE_URL",
            "TEST_DATABASE_URL",
            "AUTH_SECRET",
            "OPENAI_API_KEY",
        ):
            os.environ.pop(name, None)
    port = int(sys.argv[1])
    state_file = Path(sys.argv[2]).resolve()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with fixture_database(state_file, "--resume" in sys.argv[3:]) as url:
        engine = create_engine(normalize_url(url))
        with engine.begin() as connection:
            migrate(connection, target="head")
        engine.dispose()
        settings = Settings(
            _env_file=None,
            workflow_v2=True,
            llm_workflow=True,
            database_url=SecretStr(url),
            auth_secret=SecretStr("react-browser-synthetic-secret-at-least-32-characters"),
            openai_api_key=SecretStr(""),
            openai_model="controlled",
            production=False,
            allowed_origins=("http://127.0.0.1:3000", "http://localhost:3000"),
            llm_input_rate_bound=Decimal(".000001"),
            llm_output_rate_bound=Decimal(".000002"),
        )
        app = create_app(settings)
        original_lifespan = app.router.lifespan_context
        control = {"saveFailure": False, "providerCalls": 0, "saveAttempts": []}

        class Adapter:
            async def request(self, request, timeout):
                control["providerCalls"] += 1
                user = next(
                    (item["content"] for item in request.messages if item["role"] == "user"), "{}"
                )
                facts = json.loads(user)
                locale = facts.get("locale", facts.get("interfaceLocale", "en"))
                if locale not in ("ru", "en"):
                    locale = "en"
                language = facts.get("selection", {}).get("selectedLanguage", "en")
                if language not in ("ru", "en", "es"):
                    language = "en"
                value = output(request.schema_name, locale, language)
                # The current native prose schema adds trusted labels server-side.
                value.pop("labels", None)
                if request.schema_name == "reply_v1":
                    value["text"] = {
                        "en": (
                            "I can prepare a separate proposal for these extra deliverables. "
                            "Please approve the additional work before implementation."
                        ),
                        "es": (
                            "Puedo preparar una propuesta para estos entregables adicionales. "
                            "Confirme el trabajo adicional antes de comenzar."
                        ),
                        "ru": (
                            "Подготовлю отдельное предложение по дополнительным задачам. "
                            "Пожалуйста, согласуйте работы до начала реализации."
                        ),
                    }[language]
                if facts.get("action") == "translate":
                    value["commercialTerms"] = translation_commercial_terms(facts)
                if request.schema_name == "analysis_v1":
                    value["citations"] = [facts["project"]["scope"][:100]]
                    value["currency"] = facts["project"].get("currency") or "USD"
                return ProviderResponse(
                    json.dumps(value, ensure_ascii=False),
                    model="controlled",
                    provider="fixture",
                    input_tokens=10,
                    output_tokens=10,
                )

        @asynccontextmanager
        async def lifespan(application):
            async with original_lifespan(application):
                database = application.state.database

                def factory():
                    return WorkflowUnitOfWork(database.new_uow())

                store = LlmSQLStore(database.new_uow)
                runner = StructuredStageRunner(ProviderGateway(store, Adapter()), store)
                worker = LlmWorker(factory, store, runner, poll_interval=0.05)
                storage = FilesystemObjectStorage(state_file.parent / "objects")
                application.state.export_storage = storage
                exports = ExportWorker(
                    factory, storage, DocumentRendering(application.state.technical_operations)
                )
                task = asyncio.create_task(worker.run())

                async def export_loop():
                    while True:
                        if not await exports.process_one():
                            await asyncio.sleep(0.05)

                exporter = asyncio.create_task(export_loop())
                state_file.write_text(
                    json.dumps(
                        {
                            "apiOrigin": f"http://127.0.0.1:{port}",
                            "databaseUrl": url,
                            "disposableOnly": True,
                        }
                    ),
                    encoding="utf-8",
                )
                try:
                    yield
                finally:
                    worker.stopping.set()
                    exporter.cancel()
                    await asyncio.gather(task, exporter, return_exceptions=True)

        app.router.lifespan_context = lifespan

        @app.middleware("http")
        async def save_fault(request: Request, call_next):
            if request.method == "PUT" and request.url.path.startswith("/api/v2/drafts/"):
                body = await request.json()
                control["saveAttempts"].append(
                    {
                        "draftId": request.url.path.split("/")[-1],
                        "operationId": body.get("operationId"),
                    }
                )
                if control["saveFailure"]:
                    return JSONResponse({"error": "errors.requestFailed"}, 503)
            return await call_next(request)

        @app.post("/__test/control", include_in_schema=False)
        async def set_control(request: Request):
            body = await request.json()
            control["saveFailure"] = bool(body.get("saveFailure", False))
            if body.get("shutdown"):
                server.should_exit = True
            return {"ok": True}

        @app.get("/__test/evidence", include_in_schema=False)
        async def evidence():
            database = app.state.database
            async with database.engine.connect() as connection:
                counts = {}
                for table in (
                    "users",
                    "projects",
                    "drafts",
                    "history_entries",
                    "activity_events",
                    "llm_operations",
                    "provider_calls",
                ):
                    counts[table] = await connection.scalar(text(f"SELECT count(*) FROM {table}"))
            return {**control, "counts": counts}

        # Bind loopback plus the Docker host interface for the owned static image.
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="0.0.0.0",
                port=port,
                log_level="warning",
                loop="scope_guard.database.session:event_loop",
            )
        )
        server.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
