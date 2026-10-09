"""Exact mapping of the Drizzle schema after migration 0006; no runtime DDL."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from scope_guard.core.contracts import Currency, EvaluationAccuracy, Industry, PricingModel, Verdict


class Base(DeclarativeBase):
    pass


def enum_type(enum, name):
    return ENUM(enum, name=name, values_callable=lambda values: [item.value for item in values])


industry = enum_type(Industry, "industry")
verdict = enum_type(Verdict, "verdict")
pricing_model = enum_type(PricingModel, "pricing_model")
currency = enum_type(Currency, "currency")
accuracy = enum_type(EvaluationAccuracy, "evaluation_accuracy")


def pk():
    return mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def timestamp():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def fk(target, name):
    return ForeignKey(target, name=name, ondelete="CASCADE", onupdate="NO ACTION")


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="users_email_unique"),)
    id: Mapped[UUID] = pk()
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp()


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            """
      (start_date IS NULL AND pricing_model IS NULL AND currency IS NULL AND hourly_rate IS NULL
AND fixed_price IS NULL)
      OR (start_date IS NOT NULL AND currency IS NOT NULL AND (
        (pricing_model = 'hourly' AND hourly_rate > 0 AND fixed_price IS NULL)
        OR (pricing_model = 'fixed' AND fixed_price > 0 AND hourly_rate IS NULL)))
    """,
            name="projects_commercial_terms_consistent",
        ),
    )
    id: Mapped[UUID] = pk()
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), fk("users.id", "projects_user_id_users_id_fk")
    )
    name: Mapped[str] = mapped_column(Text)
    client: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[Industry] = mapped_column(industry)
    scope: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    pricing_model: Mapped[PricingModel | None] = mapped_column(pricing_model)
    currency: Mapped[Currency | None] = mapped_column(currency)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fixed_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    last_checked: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = timestamp()


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


class DraftRow(Base):
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


class EvaluationCaseRow(Base):
    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint("history_entry_id", name="evaluation_cases_history_entry_id_unique"),
        CheckConstraint(
            """
          (accuracy = 'debatable' AND human_verdict IS NULL)
          OR (accuracy = 'correct' AND human_verdict IS NOT NULL AND human_verdict = ai_verdict)
          OR (accuracy = 'wrong' AND human_verdict IS NOT NULL AND human_verdict <> ai_verdict)
        """,
            name="evaluation_cases_accuracy_human_verdict",
        ),
    )
    id: Mapped[UUID] = pk()
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), fk("users.id", "evaluation_cases_user_id_users_id_fk")
    )
    history_entry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        fk("history_entries.id", "evaluation_cases_history_entry_id_history_entries_id_fk"),
    )
    scope: Mapped[str] = mapped_column(Text)
    request: Mapped[str] = mapped_column(Text)
    ai_verdict: Mapped[Verdict] = mapped_column(verdict)
    human_verdict: Mapped[Verdict | None] = mapped_column(verdict)
    ai_reasoning: Mapped[str] = mapped_column(Text)
    accuracy: Mapped[EvaluationAccuracy] = mapped_column(accuracy)
    industry: Mapped[Industry] = mapped_column(industry)
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()
