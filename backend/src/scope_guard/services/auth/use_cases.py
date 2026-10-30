from collections.abc import Callable
from uuid import UUID

from scope_guard.domain.auth.repository import AuthWork, DuplicateEmail
from scope_guard.domain.auth.validation import AuthError, credentials
from scope_guard.services.auth.ports import PasswordPort, SessionPort


class AuthService:
    def __init__(
        self,
        work: Callable[[], AuthWork] | None,
        passwords: PasswordPort,
        sessions: SessionPort | None,
    ):
        self.work, self.passwords, self.sessions = work, passwords, sessions

    def configured(self) -> tuple[Callable[[], AuthWork], SessionPort]:
        if self.work is None or self.sessions is None:
            raise AuthError("errors.requestFailed", 500)
        return self.work, self.sessions

    async def register(self, body: dict) -> tuple[dict[str, str], str]:
        email, password = credentials(body)
        factory, sessions = self.configured()
        async with factory() as work:
            if await work.users.by_email(email):
                raise AuthError("errors.duplicateEmail", 409)
        # Hashing holds no database connection/transaction.
        hashed = await self.passwords.hash(password)
        try:
            async with factory() as work:
                record = await work.users.insert(email, hashed)
                user = record.public()
                token = sessions.issue({**user, "session_version": record.session_version})
                await work.commit()
                return user, token
        except DuplicateEmail:
            raise AuthError("errors.duplicateEmail", 409) from None

    async def login(self, body: dict) -> tuple[dict[str, str], str]:
        email, password = credentials(body)
        factory, sessions = self.configured()
        async with factory() as work:
            user = await work.users.by_email(email)
        if user is None or not await self.passwords.verify(password, user.password_hash):
            raise AuthError("errors.invalidCredentials", 401)
        public = user.public()
        return public, sessions.issue({**public, "session_version": user.session_version})

    async def me(self, token: str | None) -> dict[str, str]:
        if not token:
            raise AuthError("errors.authRequired", 401)
        factory, sessions = self.configured()
        claims = sessions.verify(token)
        if claims is None:
            raise AuthError("errors.authRequired", 401)
        try:
            identifier = UUID(str(claims["id"]))
        except ValueError:
            raise AuthError("errors.authRequired", 401) from None
        async with factory() as work:
            user = await work.users.by_id(identifier)
        if user is None or user.session_version != claims.get("session_version", 0):
            raise AuthError("errors.authRequired", 401)
        return user.public()
