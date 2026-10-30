from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str = field(repr=False)

    session_version: int = 0

    email_verified_at: datetime | None = None
    email_verification_required: bool = False

    def public(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "email": self.email,
            "workspaceAccess": "allowed"
            if self.email_verified_at is not None or not self.email_verification_required
            else "email_confirmation_required",
        }


class DuplicateEmail(Exception):
    pass
