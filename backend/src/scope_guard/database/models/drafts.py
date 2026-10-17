from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from scope_guard.database.models.base import Base, fk, pk, timestamp

"""Historical Drizzle baseline mapping; current schema uses models.workflow Core tables."""


class CompatibilityDraftRow(Base):
    __tablename__ = "drafts"
    __table_args__ = (
        UniqueConstraint("history_entry_id", name="drafts_history_entry_id_unique"),
        Index("drafts_project_creation_key_unique", "project_id", "idempotency_key", unique=True),
        Index("drafts_project_created_at_idx", "project_id", "created_at"),
        CheckConstraint("status = 'draft'", name="drafts_status_valid"),
        CheckConstraint("locale IN ('ru', 'en')", name="drafts_locale_valid"),
    )
    id: Mapped[UUID] = pk()
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), fk("projects.id", "drafts_project_id_projects_id_fk")
    )
    history_entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        fk("history_entries.id", "drafts_history_entry_id_history_entries_id_fk"),
    )
    idempotency_key: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    project_snapshot: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    analysis_snapshot: Mapped[dict] = mapped_column(JSONB)
    draft_document: Mapped[dict] = mapped_column(JSONB)
    locale: Mapped[str] = mapped_column(Text)
    request_language: Mapped[str | None] = mapped_column(Text)
    client_material_language: Mapped[str] = mapped_column(Text)
    change_order_labels: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()


# Retained import for frozen baseline clients. Current mappings live in workflow.py.
DraftRow = CompatibilityDraftRow
