"""Exercise the production scheduler, including its task and heartbeat ownership."""

import asyncio
from collections import Counter, deque
from datetime import UTC, datetime, timedelta

import pytest

from scope_guard.services.llm.worker import LlmWorker


class Store:
    def __init__(self, jobs=()):
        self.jobs = deque(jobs)
        self.claims = Counter()
        self.abandoned = []
        self.renewed = asyncio.Event()
        self.failed = []
        self.claimed = {lane: asyncio.Event() for lane in ("user", "diagnostic")}
        self.idle = {lane: asyncio.Event() for lane in ("user", "diagnostic")}

    async def claim(self, worker, *, lane):
        self.claims[lane] += 1
        self.claimed[lane].set()
        for job in self.jobs:
            if (job["kind"] == "diagnostic") == (lane == "diagnostic"):
                self.jobs.remove(job)
                return job
        self.idle[lane].set()
        return None

    async def renew(self, identifier, epoch):
        self.renewed.set()
        return True

    async def abandon(self, identifier, epoch):
        self.abandoned.append(identifier)

    async def fail(self, identifier, epoch, code, status):
        self.failed.append(identifier)

    def is_transient(self, error):
        return False


def job(identifier, kind):
    return dict(
        id=identifier, kind=kind, epoch=1, deadline_at=datetime.now(UTC) + timedelta(minutes=1)
    )


@pytest.mark.parametrize("shutdown", ["stop", "cancel"])
def test_serial_lanes_keep_user_capacity_and_await_all_shutdown_cleanup(shutdown):
    async def exercise():
        store = Store(
            [job(1, "diagnostic"), job(2, "diagnostic"), job(3, "check"), job(4, "check")]
        )
        active, maximum = Counter(), Counter()
        entered = {identifier: asyncio.Event() for identifier in range(1, 5)}
        release = {identifier: asyncio.Event() for identifier in range(1, 5)}

        class Worker(LlmWorker):
            async def execute(self, operation):
                identifier, kind = operation["id"], operation["kind"]
                active[kind] += 1
                maximum[kind] = max(maximum[kind], active[kind])
                entered[identifier].set()
                try:
                    await release[identifier].wait()
                finally:
                    active[kind] -= 1

        baseline = asyncio.all_tasks()
        worker = Worker(None, store, None, heartbeat_interval=0.01, shutdown_timeout=0.02)
        running = asyncio.create_task(worker.run())
        await asyncio.wait_for(asyncio.gather(entered[1].wait(), entered[3].wait()), 2)
        assert not entered[2].is_set() and not entered[4].is_set()
        release[3].set()
        await asyncio.wait_for(entered[4].wait(), 2)
        assert not release[1].is_set() and not entered[2].is_set()
        await asyncio.wait_for(store.renewed.wait(), 2)
        if shutdown == "stop":
            worker.stopping.set()
            await asyncio.wait_for(running, 2)
        else:
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(running, 2)
        assert maximum == {"diagnostic": 1, "check": 1}
        assert active == {"diagnostic": 0, "check": 0}
        assert set(store.abandoned) == {1, 4}
        assert not store.failed
        assert not asyncio.all_tasks() - baseline

    asyncio.run(exercise())


def test_lost_diagnostic_lease_cancels_only_its_execution_and_continues_lane():
    async def exercise():
        cancelled, next_review, user_done = asyncio.Event(), asyncio.Event(), asyncio.Event()

        class LeaseStore(Store):
            async def renew(self, identifier, epoch):
                return identifier != 1

        store = LeaseStore([job(1, "diagnostic"), job(2, "diagnostic"), job(3, "check")])

        class Worker(LlmWorker):
            async def execute(self, operation):
                if operation["id"] == 1:
                    try:
                        await asyncio.Event().wait()
                    finally:
                        cancelled.set()
                elif operation["id"] == 2:
                    next_review.set()
                else:
                    user_done.set()

        worker = Worker(None, store, None, heartbeat_interval=0.01)
        running = asyncio.create_task(worker.run())
        try:
            await asyncio.wait_for(asyncio.gather(next_review.wait(), user_done.wait()), 2)
            assert cancelled.is_set()
            assert not store.abandoned and not store.failed
        finally:
            worker.stopping.set()
            await asyncio.wait_for(running, 2)

    asyncio.run(exercise())


def test_idle_lanes_wait_and_claim_failure_does_not_stop_other_lane():
    async def exercise():
        class FailingStore(Store):
            async def claim(self, worker, *, lane):
                result = await super().claim(worker, lane=lane)
                if lane == "diagnostic":
                    raise RuntimeError("controlled claim failure")
                return result

        store = FailingStore([job(1, "check")])
        completed = asyncio.Event()

        class Worker(LlmWorker):
            async def execute(self, operation):
                completed.set()

        worker = Worker(None, store, None, poll_interval=60)
        running = asyncio.create_task(worker.run())
        await asyncio.wait_for(store.claimed["diagnostic"].wait(), 2)
        await asyncio.wait_for(completed.wait(), 2)
        # Both lanes have reached their wait; an event-loop barrier needs no sleep.
        await asyncio.wait_for(store.idle["user"].wait(), 2)
        worker.stopping.set()
        await asyncio.wait_for(running, 2)
        assert store.claims == {"user": 2, "diagnostic": 1}

    asyncio.run(exercise())
