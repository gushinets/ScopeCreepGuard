from typing import Protocol


class PasswordPort(Protocol):
    async def hash(self, password: str) -> str: ...
    async def verify(self, password: str, hashed: str) -> bool: ...


class SessionPort(Protocol):
    def issue(self, user: dict[str, str]) -> str: ...
    def verify(self, token: str) -> dict[str, str] | None: ...


SESSION_COOKIE_NAME = "scg_session"
SESSION_MAX_AGE_SECONDS = 604800
