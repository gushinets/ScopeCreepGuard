"""Fail closed if a compatibility writer is accidentally used after v2 contraction."""

from sqlalchemy import text

from scope_guard.domain.drafts.workflow import WorkflowError


async def supports_legacy_schema(session) -> bool:
    version = await session.scalar(text("SELECT version_num FROM public.alembic_version"))
    return version in {"0001_existing_drizzle_schema", "0002_workflow_expand"}


async def require_legacy_schema(session) -> None:
    if not await supports_legacy_schema(session):
        raise WorkflowError("clientUpgradeRequired", 426)
