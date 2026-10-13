"""Fail closed if a compatibility writer is accidentally used after v2 contraction."""

from sqlalchemy import text

from scope_guard.domain.drafts.workflow import WorkflowError


async def require_legacy_schema(session) -> None:
    version = await session.scalar(text("SELECT version_num FROM public.alembic_version"))
    if version not in {"0001_existing_drizzle_schema", "0002_workflow_expand"}:
        raise WorkflowError("clientUpgradeRequired", 426)
