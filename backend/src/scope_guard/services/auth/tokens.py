"""Internal email-flow operations. Never log arguments or return these in HTTP users.

Issuance linearizes at the user lock: an issuance ordered before reset is
revoked by reset; one ordered after it is a genuinely new reset request.
Every write locks users first. Password hashing holds no database connection.
"""

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from scope_guard.domain.auth.repository import AuthTokenWork
from scope_guard.domain.auth.tokens import InvalidAuthToken, IssuedAuthToken, Purpose
from scope_guard.services.auth.ports import PasswordPort


def digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def check_purpose(purpose: Purpose) -> None:
    if purpose not in ("verify_email", "reset_password"):
        raise InvalidAuthToken()


class AuthTokenService:
    def __init__(
        self,
        work: Callable[[], AuthTokenWork],
        passwords: PasswordPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.work, self.passwords, self.clock = work, passwords, clock

    async def issue(self, user_id: UUID, purpose: Purpose) -> IssuedAuthToken:
        check_purpose(purpose)
        raw = secrets.token_urlsafe(32)
        async with self.work() as work:
            await work.tokens.lock_user(user_id)
            now = self.clock()
            expires = now + timedelta(hours=24)
            await work.tokens.insert(user_id, purpose, digest(raw), now, expires)
            await work.commit()
        return IssuedAuthToken(raw, expires)

    async def issue_pending_confirmation(self, user_id: UUID) -> IssuedAuthToken:
        raw = secrets.token_urlsafe(32)
        async with self.work() as work:
            await work.tokens.lock_user(user_id)
            if not await work.tokens.confirmation_pending(user_id):
                raise InvalidAuthToken()
            now = self.clock()
            expires = now + timedelta(hours=24)
            await work.tokens.insert(user_id, "verify_email", digest(raw), now, expires)
            await work.commit()
        return IssuedAuthToken(raw, expires)

    async def inspect(self, user_id: UUID, purpose: Purpose, raw: str) -> bool:
        check_purpose(purpose)
        async with self.work() as work:
            return await work.tokens.valid(user_id, purpose, digest(raw), self.clock()) is not None

    async def revoke(self, user_id: UUID, purpose: Purpose) -> None:
        check_purpose(purpose)
        async with self.work() as work:
            await work.tokens.lock_user(user_id)
            await work.tokens.revoke(user_id, purpose, self.clock())
            await work.commit()

    async def confirm_email(self, user_id: UUID, raw: str) -> None:
        await self._apply(user_id, "verify_email", raw)

    async def reset_password(self, user_id: UUID, raw: str, password: str) -> None:
        from scope_guard.domain.auth.validation import credentials

        # Reuse the current password policy without needing the real user's email.
        credentials({"email": "validation@example.test", "password": password})
        if not await self.inspect(user_id, "reset_password", raw):
            raise InvalidAuthToken()
        hashed = await self.passwords.hash(password)
        await self._apply(user_id, "reset_password", raw, hashed)

    async def _apply(self, user_id, purpose, raw, hashed=None):
        async with self.work() as work:
            await work.tokens.lock_user(user_id)
            now = self.clock()
            token_id = await work.tokens.valid(user_id, purpose, digest(raw), now)
            if token_id is None:
                raise InvalidAuthToken()
            await work.tokens.apply(user_id, purpose, token_id, now, hashed)
            await work.commit()
