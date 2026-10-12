from dataclasses import dataclass, field
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
