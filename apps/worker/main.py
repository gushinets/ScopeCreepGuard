"""Export worker composition root. API owns migrations; this process only serves jobs."""

import asyncio
import logging

from scope_guard.core.config import Settings
from scope_guard.database.repositories.workflow import WorkflowUnitOfWork
from scope_guard.database.session import create_database, event_loop
from scope_guard.integrations.documents.technical.operations import TechnicalOperations
from scope_guard.integrations.storage.s3 import S3ObjectStorage
from scope_guard.services.documents.export_worker import ExportWorker
from scope_guard.services.documents.rendering import DocumentRendering


async def main():
    settings = Settings()
    database = create_database(settings)
    if database is None or not settings.export_bucket:
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
        await worker.run()
    finally:
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(), loop_factory=event_loop)
