"""Worker composition root. The one-shot migration service owns schema changes."""

import asyncio
import logging
import signal
from pathlib import Path

from scope_guard.core.config import Settings
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import create_database, event_loop
from scope_guard.integrations.documents.technical.operations import TechnicalOperations
from scope_guard.integrations.storage.s3 import S3ObjectStorage
from scope_guard.services.documents.export_worker import ExportWorker
from scope_guard.services.documents.rendering import DocumentRendering
from sqlalchemy import text


async def serve(worker, database):
    """Publish readiness only while the worker loop and database remain available."""
    marker = Path("/tmp/scope-guard-worker-ready")
    marker.unlink(missing_ok=True)

    async def heartbeat():
        while True:
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            marker.touch()
            await asyncio.sleep(10)

    logging.getLogger("scope_guard").info("worker_ready schema_verified=true")
    try:
        async with asyncio.TaskGroup() as tasks:
            probe = tasks.create_task(heartbeat())

            async def run():
                try:
                    await worker.run()
                finally:
                    probe.cancel()

            tasks.create_task(run())
    finally:
        marker.unlink(missing_ok=True)


async def main():
    Path("/tmp/scope-guard-worker-ready").unlink(missing_ok=True)
    settings = Settings()
    database = create_database(settings)
    if database is None:
        raise RuntimeError("Worker requires database configuration")
    from scope_guard.database.schema_verification import verify_nonblocking_schema

    async with database.engine.begin() as connection:
        await connection.run_sync(verify_nonblocking_schema)
    if settings.worker_role == "llm":
        from scope_guard.database.repositories.llm import LlmSQLStore
        from scope_guard.integrations.llm.gateway import ProviderGateway
        from scope_guard.integrations.llm.litellm_adapter import LiteLLMResponsesAdapter
        from scope_guard.integrations.llm.stages import StructuredStageRunner
        from scope_guard.services.llm.worker import LlmWorker

        if not settings.llm_workflow or not settings.workflow_v2 or not settings.openai_api_key:
            raise RuntimeError("LLM worker requires workflow flags and provider configuration")
        store = LlmSQLStore(database.new_uow)
        adapter = LiteLLMResponsesAdapter(settings.openai_api_key.get_secret_value())
        worker = LlmWorker(
            lambda: WorkflowUnitOfWork(database.new_uow()),
            store,
            StructuredStageRunner(ProviderGateway(store, adapter), store),
        )
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, worker.stopping.set)
            except NotImplementedError:
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(worker.stopping.set))
        try:
            await serve(worker, database)
        finally:
            await adapter.close()
            await database.close()
        return
    if not settings.export_bucket:
        raise RuntimeError("Worker requires database and private export bucket configuration")
    storage = S3ObjectStorage(
        settings.export_bucket,
        endpoint=settings.export_endpoint or None,
        region=settings.export_region,
        access_key=settings.export_access_key.get_secret_value()
        if settings.export_access_key
        else None,
        secret_key=settings.export_secret_key.get_secret_value()
        if settings.export_secret_key
        else None,
    )
    worker = ExportWorker(
        lambda: WorkflowUnitOfWork(database.new_uow()),
        storage,
        DocumentRendering(TechnicalOperations()),
        retention_days=settings.export_retention_days,
    )
    try:
        await serve(worker, database)
    finally:
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(), loop_factory=event_loop)
