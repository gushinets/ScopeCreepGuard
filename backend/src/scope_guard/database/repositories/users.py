from typing import Self
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.database.models.workflow import WORKFLOW_METADATA
from scope_guard.database.repositories.auth_tokens import AuthTokens
from scope_guard.database.unit_of_work import SqlAlchemyUnitOfWork
from scope_guard.domain.auth.repository import DuplicateEmail, User

users = WORKFLOW_METADATA.tables["users"]


class Users:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_email(self, email: str) -> User | None:
        row = (
            (await self.session.execute(select(users).where(users.c.email == email)))
            .mappings()
            .one_or_none()
        )
        return User(row.id, row.email, row.password_hash, row.session_version) if row else None

    async def by_id(self, identifier: UUID) -> User | None:
        row = (
            (await self.session.execute(select(users).where(users.c.id == identifier)))
            .mappings()
            .one_or_none()
        )
        return User(row.id, row.email, row.password_hash, row.session_version) if row else None

    async def insert(self, email: str, password_hash: str) -> User:
        try:
            row = (
                (
                    await self.session.execute(
                        insert(users)
                        .values(email=email, password_hash=password_hash)
                        .returning(users)
                    )
                )
                .mappings()
                .one()
            )
        except IntegrityError as error:
            diagnostic = getattr(error.orig, "diag", None)
            if getattr(diagnostic, "constraint_name", None) == "users_email_unique":
                raise DuplicateEmail() from None
            raise
        from scope_guard.database.repositories.activity import profiles_supported
        from scope_guard.database.repositories.profiles import Profiles

        if await profiles_supported(self.session):
            await Profiles(self.session).create(row.id)
        return User(row.id, row.email, row.password_hash, row.session_version)


class AuthUnitOfWork:
    def __init__(self, work: SqlAlchemyUnitOfWork):
        self.work = work
        self.users: Users
        self.tokens: AuthTokens

    async def __aenter__(self) -> Self:
        await self.work.__aenter__()
        self.users = Users(self.work.session)
        self.tokens = AuthTokens(self.work.session)
        return self

    async def commit(self) -> None:
        await self.work.commit()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.work.__aexit__(exc_type, exc, traceback)
