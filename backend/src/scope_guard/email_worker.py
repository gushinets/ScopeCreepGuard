"""Email process composition root; schema is verified, never migrated here."""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import text

from scope_guard.core.config import Settings
from scope_guard.database.repositories.password_recovery import RecoveryQueue
from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.database.schema_verification import verify_password_recovery_schema
from scope_guard.database.session import create_database, event_loop
from scope_guard.integrations.auth.passwords import Passwords
from scope_guard.integrations.email.smtp import SMTPSender
from scope_guard.services.auth.tokens import AuthTokenService
from scope_guard.services.email.recovery_worker import RecoveryWorker
from scope_guard.services.email.service import EmailService


async def serve(worker, database):
    """Health reports a live email loop and database, never SMTP availability."""
    marker = Path("/tmp/scope-guard-email-ready")
    marker.unlink(missing_ok=True)

    async def heartbeat():
        while True:
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            marker.touch()
            await asyncio.sleep(10)

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
    Path("/tmp/scope-guard-email-ready").unlink(missing_ok=True)
    settings = Settings()
    database = create_database(settings)
    if database is None or not settings.auth_secret or not settings.public_app_url:
        raise RuntimeError("Email worker requires database, AUTH_SECRET and PUBLIC_APP_URL")
    try:
        async with database.engine.begin() as connection:
            if (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                != "0011_password_recovery"
            ):
                raise RuntimeError("Email worker requires the password recovery migration revision")
            await connection.run_sync(verify_password_recovery_schema)
        queue = RecoveryQueue(database.new_uow, settings.auth_secret.get_secret_value())
        tokens = AuthTokenService(lambda: AuthUnitOfWork(database.new_uow()), Passwords())
        await serve(
            RecoveryWorker(
                queue, tokens, EmailService(SMTPSender(settings)), settings.public_app_url
            ),
            database,
        )
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with asyncio.Runner(loop_factory=event_loop) as runner:
        runner.run(main())
