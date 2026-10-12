from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from scope_guard.database.models.base import (
    Base,
    currency,
    fk,
    industry,
    pk,
    pricing_model,
    timestamp,
)
from scope_guard.domain.shared.enums import (
    Currency,
    Industry,
    PricingModel,
)

"""Exact mapping of the Drizzle schema after migration 0006; no runtime DDL."""


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
