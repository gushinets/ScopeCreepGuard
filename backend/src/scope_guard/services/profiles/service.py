from collections.abc import Callable

from scope_guard.domain.drafts.workflow import WorkflowError
from scope_guard.domain.profiles.repository import ProfilesWork
from scope_guard.services.drafts.workflow import expected, key


class ProfileService:
    def __init__(self, factory: Callable[[], ProfilesWork]):
        self.factory = factory

    async def onboarding(self, owner, event=None):
        async with self.factory() as work:
            result = await work.profiles.onboarding(owner, event)
            if event is not None:
                await work.commit()
            return result

    async def get(self, owner):
        async with self.factory() as work:
            return await work.profiles.get(owner)

    async def update(self, owner, body):
        if body.keys() - {"operationId", "expectedRevision", "changes"}:
            raise WorkflowError("profileInvalid")
        async with self.factory() as work:
            result = await work.profiles.update(
                owner, expected(body), key(body), body.get("changes")
            )
            await work.commit()
            return result

    async def observe(self, owner):
        async with self.factory() as work:
            await work.profiles.observe(owner)
            await work.commit()
