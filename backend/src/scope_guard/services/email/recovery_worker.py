"""Email-only orchestration. No database transaction spans SMTP."""

import asyncio
import json
import logging
import random
from time import monotonic

from scope_guard.services.email.contracts import EmailError

logger = logging.getLogger("scope_guard.email_worker")


class RecoveryWorker:
    def __init__(self, queue, tokens, email, public_url):
        self.queue, self.tokens, self.email, self.public_url = queue, tokens, email, public_url

    async def prepare(self, job):
        return await self.queue.prepare(job, self.tokens, self.public_url)

    async def once(self):
        job = await self.queue.claim()
        if not job:
            return False
        started = monotonic()
        try:
            prepared = await self.prepare(job)
            if prepared is None:
                return True
            recipient, url = prepared
            try:
                async with asyncio.timeout(30):
                    if job["purpose"] == "password_changed":
                        await self.email.send_password_changed(recipient, job["locale"])
                    else:
                        await self.email.send_password_recovery(recipient, url, job["locale"])
            except TimeoutError:
                raise EmailError("ambiguous") from None
            await self.queue.finish(job["id"], job["lease_owner"], "accepted")
            logger.info(
                json.dumps(
                    {
                        "event": "email_job_result",
                        "job_id": str(job["id"]),
                        "purpose": job["purpose"],
                        "attempt": job["attempts"],
                        "category": "accepted",
                        "duration_ms": round((monotonic() - started) * 1000),
                    }
                )
            )
        except EmailError as error:
            retry = error.category in ("temporary", "ambiguous") and job["attempts"] < 5
            delay = (60, 300, 900, 3600)[min(job["attempts"] - 1, 3)] if retry else 0
            await self.queue.finish(
                job["id"],
                job["lease_owner"],
                "pending" if retry else "failed",
                error.category,
                delay + random.randrange(0, 11) if retry else 0,
            )
            logger.info(
                json.dumps(
                    {
                        "event": "email_job_result",
                        "job_id": str(job["id"]),
                        "purpose": job["purpose"],
                        "attempt": job["attempts"],
                        "category": error.category,
                        "duration_ms": round((monotonic() - started) * 1000),
                    }
                )
            )
        return True

    async def run(self):
        while True:
            try:
                await self.queue.cleanup()
                if not await self.once():
                    await asyncio.sleep(1)
            except Exception:
                # Never interpolate exception/provider data into application logs.
                logger.error("email_worker_infrastructure_failure")
                await asyncio.sleep(5)
