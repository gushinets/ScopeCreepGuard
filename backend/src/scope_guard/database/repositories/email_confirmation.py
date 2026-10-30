"""Atomic reservations shared across API processes. Never holds locks during SMTP."""

import math
from datetime import timedelta

from sqlalchemy import text

from scope_guard.domain.auth.validation import AuthError
from scope_guard.services.auth.confirmation import ResendLimited


class ConfirmationAttempts:
    def __init__(self, work):
        self.work = work

    async def reserve(self, user_id, source_hash):
        async with self.work() as work:
            db = work.session
            # Global order: source advisory lock, then user row. Token writers
            # only acquire user rows and never acquire source locks.
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": "email-confirmation:" + source_hash},
            )
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT email_verified_at,email_verification_required "
                            "FROM users WHERE id=:id FOR UPDATE"
                        ),
                        {"id": user_id},
                    )
                )
                .mappings()
                .one()
            )
            if row.email_verified_at is not None or not row.email_verification_required:
                raise AuthError("errors.requestFailed", 409)
            now = await db.scalar(text("SELECT clock_timestamp()"))
            rows = (
                (
                    await db.execute(
                        text("""
                SELECT user_id,source_hash,created_at FROM email_confirmation_attempts
                WHERE created_at>:since AND (user_id=:id OR source_hash=:source)
                ORDER BY created_at
            """),
                        {"since": now - timedelta(hours=1), "id": user_id, "source": source_hash},
                    )
                )
                .mappings()
                .all()
            )
            account = [r.created_at for r in rows if r.user_id == user_id]
            source = [r.created_at for r in rows if r.source_hash == source_hash]
            until = now
            if account:
                until = max(until, account[-1] + timedelta(seconds=60))
            if len(account) >= 5:
                until = max(until, account[-5] + timedelta(hours=1))
            if len(source) >= 30:
                until = max(until, source[-30] + timedelta(hours=1))
            if until > now:
                raise ResendLimited(max(1, math.ceil((until - now).total_seconds())))
            attempt = await db.scalar(
                text("""
                INSERT INTO email_confirmation_attempts(user_id,source_hash,created_at)
                VALUES (:id,:source,:now) RETURNING id
            """),
                {"id": user_id, "source": source_hash, "now": now},
            )
            await work.commit()
            return attempt

    async def finish(self, attempt, status):
        async with self.work() as work:
            await work.session.execute(
                text("UPDATE email_confirmation_attempts SET status=:status WHERE id=:id"),
                {"id": attempt, "status": status},
            )
            await work.commit()

    async def status(self, user_id, source_hash=None):
        async with self.work() as work:
            now = await work.session.scalar(text("SELECT clock_timestamp()"))
            rows = (
                (
                    await work.session.execute(
                        text("""
                SELECT status,created_at FROM email_confirmation_attempts
                WHERE user_id=:id ORDER BY created_at DESC LIMIT 5
            """),
                        {"id": user_id},
                    )
                )
                .mappings()
                .all()
            )
            until = now
            if rows:
                until = rows[0].created_at + timedelta(seconds=60)
                if len(rows) == 5:
                    until = max(until, rows[-1].created_at + timedelta(hours=1))
            if source_hash is not None:
                source = (
                    (
                        await work.session.execute(
                            text("""
                    SELECT created_at FROM email_confirmation_attempts
                    WHERE source_hash=:source AND created_at>:since
                    ORDER BY created_at DESC LIMIT 30
                """),
                            {"source": source_hash, "since": now - timedelta(hours=1)},
                        )
                    )
                    .scalars()
                    .all()
                )
                if len(source) == 30:
                    until = max(until, source[-1] + timedelta(hours=1))
            return {
                "status": rows[0].status if rows else "not_attempted",
                "retryAfter": max(0, math.ceil((until - now).total_seconds())),
            }
