import re
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from scope_guard.modules.auth.repository import AuthWork, DuplicateEmail

JS_SPACE = r"\x09-\x0d\x20\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
EMAIL = re.compile(rf"^[^{JS_SPACE}@]+@[^{JS_SPACE}@]+\.[^{JS_SPACE}@]+$")


class AuthError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)


def credentials(body: dict) -> tuple[str, str]:
    if not isinstance(body.get("email"), str):
        raise AuthError("errors.emailRequired", 400)
    if not isinstance(body.get("password"), str):
        raise AuthError("errors.passwordRequired", 400)
    email = re.sub(rf"^[{JS_SPACE}]+|[{JS_SPACE}]+$", "", body["email"]).lower()
    password = body["password"]
    if not EMAIL.fullmatch(email):
        raise AuthError("errors.invalidEmail", 400)
    if len(password.encode("utf-16-le", errors="surrogatepass")) // 2 < 8:
        raise AuthError("errors.passwordTooShort", 400)
    return email, password


class PasswordPort(Protocol):
    async def hash(self, password: str) -> str: ...
    async def verify(self, password: str, hashed: str) -> bool: ...


class SessionPort(Protocol):
    def issue(self, user: dict[str, str]) -> str: ...
    def verify(self, token: str) -> dict[str, str] | None: ...


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
                user = (await work.users.insert(email, hashed)).public()
                token = sessions.issue(user)
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
        return public, sessions.issue(public)

    async def me(self, token: str | None) -> dict[str, str]:
        if not token:
            raise AuthError("errors.authRequired", 401)
        factory, sessions = self.configured()
        claims = sessions.verify(token)
        if claims is None:
            raise AuthError("errors.authRequired", 401)
        try:
            identifier = UUID(claims["id"])
        except ValueError:
            raise AuthError("errors.authRequired", 401) from None
        async with factory() as work:
            user = await work.users.by_id(identifier)
        if user is None:
            raise AuthError("errors.authRequired", 401)
        return user.public()
