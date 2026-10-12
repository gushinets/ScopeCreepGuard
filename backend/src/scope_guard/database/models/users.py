from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from scope_guard.database.models.base import Base, pk, timestamp

"""Exact mapping of the Drizzle schema after migration 0006; no runtime DDL."""


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="users_email_unique"),)
    id: Mapped[UUID] = pk()
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp()
