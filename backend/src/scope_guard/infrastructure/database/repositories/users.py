from typing import Self
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.infrastructure.database.models import UserRow
from scope_guard.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.modules.auth.repository import DuplicateEmail, User


class Users:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_email(self, email: str) -> User | None:
        row = await self.session.scalar(select(UserRow).where(UserRow.email == email))
        return User(row.id, row.email, row.password_hash) if row else None

    async def by_id(self, identifier: UUID) -> User | None:
        row = await self.session.get(UserRow, identifier)
        return User(row.id, row.email, row.password_hash) if row else None

    async def insert(self, email: str, password_hash: str) -> User:
        row = UserRow(email=email, password_hash=password_hash)
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError as error:
            diagnostic = getattr(error.orig, "diag", None)
            if getattr(diagnostic, "constraint_name", None) == "users_email_unique":
                raise DuplicateEmail() from None
            raise
        return User(row.id, row.email, row.password_hash)


class AuthUnitOfWork:
    def __init__(self, work: SqlAlchemyUnitOfWork):
        self.work = work
        self.users: Users

    async def __aenter__(self) -> Self:
        await self.work.__aenter__()
        self.users = Users(self.work.session)
        return self

    async def commit(self) -> None:
        await self.work.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.work.__aexit__(exc_type, exc, traceback)
