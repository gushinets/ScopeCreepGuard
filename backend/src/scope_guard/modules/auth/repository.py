from dataclasses import dataclass, field
from typing import Protocol, Self
from uuid import UUID


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str = field(repr=False)

    def public(self) -> dict[str, str]:
        return {"id": str(self.id), "email": self.email}


class DuplicateEmail(Exception):
    pass


class UserRepository(Protocol):
    async def by_email(self, email: str) -> User | None: ...
    async def by_id(self, identifier: UUID) -> User | None: ...
    async def insert(self, email: str, password_hash: str) -> User: ...


class AuthWork(Protocol):
    @property
    def users(self) -> UserRepository: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
    async def commit(self) -> None: ...
