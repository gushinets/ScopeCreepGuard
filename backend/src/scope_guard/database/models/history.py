from datetime import date
from uuid import UUID

from sqlalchemy import (
    Date,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from scope_guard.database.models.base import Base, fk, pk, verdict
from scope_guard.domain.shared.enums import Verdict

"""Exact mapping of the Drizzle schema after migration 0006; no runtime DDL."""


class HistoryEntryRow(Base):
    __tablename__ = "history_entries"
    id: Mapped[UUID] = pk()
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), fk("projects.id", "history_entries_project_id_projects_id_fk")
    )
    date: Mapped[date] = mapped_column(Date)
    request: Mapped[str] = mapped_column(Text)
    verdict: Mapped[Verdict] = mapped_column(verdict)
    summary: Mapped[str] = mapped_column(Text)
