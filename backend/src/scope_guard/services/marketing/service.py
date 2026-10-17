from collections.abc import Callable
from datetime import date, timedelta

from scope_guard.domain.marketing import calculate, instant
from scope_guard.services.marketing.ports import MetricsUnitOfWork


class MetricsService:
    """Supported access path: read/reconcile half-open report dates [start,end).

    Each call repairs ALL history through current UTC day, including idle expiry,
    late accounting and changed feedback/exclusions. The requested range controls
    returned rows, not recovery scope. Future report dates are not materialized.
    """

    def __init__(self, factory: Callable[[], MetricsUnitOfWork]):
        self.factory = factory

    async def reconcile(self, start: date, end: date) -> list[dict]:
        if start >= end:
            raise ValueError("metrics_range_must_be_nonempty")
        async with self.factory() as work:
            observation = await work.metrics.snapshot()
            if observation is None:
                return []
            snapshot, earliest_report = observation
            first = min(start, earliest_report or start, instant(snapshot.cutoff).date())
            for records, columns in (
                (snapshot.profiles, ("registered_at",)),
                (snapshot.checks, ("completed_at",)),
                (snapshot.orders, ("finalized_at", "voided_at")),
                (snapshot.operations, ("created_at", "finished_at")),
                (snapshot.calls, ("started_at",)),
            ):
                for record in records:
                    for column in columns:
                        if record.get(column):
                            first = min(first, instant(record[column]).date())
            through = instant(snapshot.cutoff).date()
            rows = []
            while first <= through:
                rows.append(calculate(snapshot, first))
                first += timedelta(days=1)
            await work.metrics.save(rows)
            result = await work.metrics.read(start, end)
            await work.commit()
            return result

    async def read(self, start: date, end: date) -> list[dict]:
        return await self.reconcile(start, end)
