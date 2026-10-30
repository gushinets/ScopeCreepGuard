"""All writers lock the owning user before reading or mutating token state."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scope_guard.domain.auth.tokens import InvalidAuthToken, Purpose


class AuthTokens:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_user(self, user_id: UUID) -> None:
        user = await self.session.scalar(
            text("SELECT id FROM users WHERE id=:id FOR UPDATE"), {"id": user_id}
        )
        if user is None:
            raise InvalidAuthToken()

    async def confirmation_pending(self, user_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT email_verified_at IS NULL AND email_verification_required "
                    "FROM users WHERE id=:id"
                ),
                {"id": user_id},
            )
        )

    async def valid(self, user_id: UUID, purpose: Purpose, digest: str, now: datetime):
        return await self.session.scalar(
            text("""
            SELECT id FROM auth_tokens WHERE user_id=:user_id AND purpose=:purpose
            AND token_hash=:digest AND expires_at>:now AND used_at IS NULL
            AND revoked_at IS NULL
        """),
            {"user_id": user_id, "purpose": purpose, "digest": digest, "now": now},
        )

    async def insert(self, user_id, purpose, digest, now, expires):
        await self.session.execute(
            text("""
            INSERT INTO auth_tokens(user_id,purpose,token_hash,created_at,expires_at)
            VALUES (:user_id,:purpose,:digest,:now,:expires)
        """),
            {
                "user_id": user_id,
                "purpose": purpose,
                "digest": digest,
                "now": now,
                "expires": expires,
            },
        )

    async def revoke(self, user_id, purpose, now):
        await self.session.execute(
            text("""
            UPDATE auth_tokens SET revoked_at=:now WHERE user_id=:user_id
            AND purpose=:purpose AND used_at IS NULL AND revoked_at IS NULL
        """),
            {"user_id": user_id, "purpose": purpose, "now": now},
        )

    async def apply(self, user_id, purpose, token_id, now, password_hash=None):
        if purpose == "verify_email":
            await self.session.execute(
                text("""
                UPDATE users SET email_verified_at=COALESCE(email_verified_at,:now)
                WHERE id=:user_id
            """),
                {"now": now, "user_id": user_id},
            )
        else:
            await self.session.execute(
                text("""
                UPDATE users SET password_hash=:password_hash,
                session_version=session_version+1 WHERE id=:user_id
            """),
                {"password_hash": password_hash, "user_id": user_id},
            )
        await self.session.execute(
            text("UPDATE auth_tokens SET used_at=:now WHERE id=:id"), {"now": now, "id": token_id}
        )
        await self.revoke(user_id, purpose, now)
