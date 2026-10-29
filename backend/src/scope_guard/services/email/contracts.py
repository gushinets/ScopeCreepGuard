"""Email contracts. Acceptance is not inbox delivery; errors never contain provider data."""

from dataclasses import dataclass
from email.headerregistry import Address
from typing import Literal, Protocol

ErrorCategory = Literal["invalid", "temporary", "authentication", "rejected", "ambiguous"]


class EmailError(Exception):
    def __init__(self, category: ErrorCategory):
        self.category = category
        super().__init__(category)


def header(value: str) -> str:
    if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise EmailError("invalid")
    return value


def address(value: str) -> str:
    try:
        parsed = Address(addr_spec=header(value))
        if not parsed.username or not parsed.domain:
            raise ValueError
    except (ValueError, IndexError):
        raise EmailError("invalid") from None
    return value


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    text: str
    html: str
    message_id: str
    kind: Literal["confirmation", "password_recovery"]
    locale: Literal["ru", "en"]

    def __post_init__(self):
        address(self.recipient)
        header(self.subject)
        header(self.message_id)
        if self.kind not in ("confirmation", "password_recovery") or self.locale not in (
            "ru",
            "en",
        ):
            raise EmailError("invalid")


class Sender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...
