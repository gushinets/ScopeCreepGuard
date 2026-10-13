"""Restart-safe export orchestration using persisted claims and fencing tokens."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from scope_guard.domain.drafts.values import freeze_json, freeze_object
from scope_guard.services.documents.models import DocumentSource


class ExportWorker:
    def __init__(self, factory, storage, renderer, retention_days: int | None = None):
        self.factory, self.storage, self.renderer = factory, storage, renderer
        self.retention_days = retention_days

    async def process_one(self) -> bool:
        async with self.factory() as work:
            await work.workflow.recover()
            claim = await work.workflow.claim_export()
            await work.commit()
        if claim is None:
            return False

        async def renew():
            while True:
                await asyncio.sleep(30)
                async with self.factory() as work:
                    valid = await work.workflow.heartbeat(UUID(claim["id"]), claim["attemptCount"])
                    await work.commit()
                if not valid:
                    return

        heartbeat = asyncio.create_task(renew())
        metadata, error = None, None
        try:
            if (
                claim["rendererVersion"] != "reportlab-v1"
                or claim["templateVersion"] != "change-order-v1"
            ):
                raise ValueError("export_version_unavailable")
            content = claim["contentSnapshot"]
            document = dict(content["document"])
            # Finalization is user review, not evidence of client acceptance.
            data = await self.renderer.render(
                DocumentSource(freeze_object(document), freeze_json(content["projectSnapshot"]))
            )
            checksum = hashlib.sha256(data).hexdigest()
            object_key = f"exports/scg-{claim['id']}/{claim['attemptCount']}.pdf"
            await self.storage.put(object_key, data)
            metadata = {
                "objectKey": object_key,
                "checksum": checksum,
                "mimeType": "application/pdf",
                "sizeBytes": len(data),
            }
        except asyncio.CancelledError:
            # Leave the persisted lease for another worker to reclaim after expiry.
            raise
        except Exception:
            error = "export_processing_failed"
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
        async with self.factory() as work:
            await work.workflow.export_outcome(claim, metadata, error)
            await work.commit()
        return True

    async def sweep_orphans(self) -> int:
        objects = await self.storage.list()
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        removed = 0
        for item in objects:
            if item["createdAt"] >= cutoff:
                continue
            async with self.factory() as work:
                known = await work.workflow.referenced_objects()
                # A live attempt is protected even if its upload predates its commit.
                parts = item["key"].split("/")
                try:
                    if not parts[1].startswith("scg-"):
                        continue
                    identifier = UUID(parts[1].removeprefix("scg-"))
                    attempt = int(parts[2].removesuffix(".pdf"))
                except (ValueError, IndexError):
                    continue
                # Heartbeat is an atomic validity test and extends an owned live claim.
                protected = await work.workflow.heartbeat(identifier, attempt)
                known = await work.workflow.referenced_objects()
                await work.commit()
            if item["key"] not in known and not protected:
                await self.storage.remove(item["key"])
                removed += 1
        return removed

    async def run(self) -> None:
        last_sweep = datetime.now(UTC) - timedelta(hours=1)
        while True:
            if datetime.now(UTC) - last_sweep >= timedelta(hours=1):
                await self.sweep_orphans()
                if self.retention_days is not None:
                    await self.expire_ready(datetime.now(UTC) - timedelta(days=self.retention_days))
                last_sweep = datetime.now(UTC)
            if not await self.process_one():
                await asyncio.sleep(2)

    async def expire_ready(self, cutoff: datetime) -> int:
        async with self.factory() as work:
            records = await work.workflow.ready_exports_before(cutoff)
        count = 0
        for row in records:
            await self.storage.remove(row["objectKey"])
            async with self.factory() as work:
                expired = await work.workflow.expire_export(UUID(row["id"]), cutoff)
                await work.commit()
            count += int(expired)
        return count
