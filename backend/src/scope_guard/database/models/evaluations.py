from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from scope_guard.database.models.base import Base, accuracy, fk, industry, pk, timestamp, verdict
from scope_guard.domain.shared.enums import EvaluationAccuracy, Industry, Verdict

"""Historical Drizzle baseline mapping; current schema uses models.workflow Core tables."""


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
