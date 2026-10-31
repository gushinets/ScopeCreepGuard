"""Short PostgreSQL transactions only. SMTP must run outside this repository."""

import hashlib
import hmac
from uuid import uuid4

from sqlalchemy import text

from scope_guard.database.repositories.users import AuthUnitOfWork
from scope_guard.domain.auth.recovery import RecoveryLimited as RecoveryLimited
from scope_guard.domain.auth.recovery import RecoveryUnavailable as RecoveryUnavailable
from scope_guard.services.auth.tokens import digest


async def capacity(db, purpose):
    # Fixed advisory lock serializes the bounded count and insert, including notifications.
    await db.execute(text("SELECT pg_advisory_xact_lock(782001)"))
    maximum = 10000 if purpose == "password_recovery" else 1000
    count = await db.scalar(
        text("""SELECT count(*) FROM email_jobs WHERE purpose=:p
        AND state IN ('pending','leased')"""),
        {"p": purpose},
    )
    if count >= maximum:
        raise RecoveryUnavailable()


class RecoveryQueue:
    def __init__(self, work, secret):
        self.work, self.secret = work, secret

    def key(self, purpose, value):
        return hmac.new(
            self.secret.encode(), f"{purpose}:{value}".encode(), hashlib.sha256
        ).hexdigest()

    async def _counter(self, db, key, seconds, maximum):
        # Every admission takes the global lock first, so cardinality checks and windows are atomic.
        count = await db.scalar(text("SELECT count(*) FROM recovery_limits"))
        exists = await db.scalar(text("SELECT 1 FROM recovery_limits WHERE id=:id"), {"id": key})
        if not exists and count >= 50000:
            raise RecoveryLimited()
        row = (
            await db.execute(
                text("""
          INSERT INTO recovery_limits(id,window_started_at,count,expires_at)
          VALUES (:id,clock_timestamp(),1,clock_timestamp()+make_interval(secs=>:seconds))
          ON CONFLICT(id) DO UPDATE SET
          count=CASE WHEN recovery_limits.expires_at<=clock_timestamp() THEN 1
            ELSE LEAST(recovery_limits.count+1,:maximum+1) END,
          window_started_at=CASE WHEN recovery_limits.expires_at<=clock_timestamp()
            THEN clock_timestamp() ELSE recovery_limits.window_started_at END,
          expires_at=CASE WHEN recovery_limits.expires_at<=clock_timestamp()
            THEN clock_timestamp()+make_interval(secs=>:seconds) ELSE recovery_limits.expires_at END
          RETURNING count
        """),
                {"id": key, "seconds": seconds, "maximum": maximum},
            )
        ).scalar_one()
        return row <= maximum

    async def limit(self, db, source, reset=False):
        await db.execute(text("SET LOCAL lock_timeout='2s'"))
        await db.execute(text("SET LOCAL statement_timeout='5s'"))
        await db.execute(text("SELECT pg_advisory_xact_lock(782002)"))
        prefix = "reset" if reset else "request"
        rules = [("global-minute", 60, 300 if reset else 100)]
        if not reset:
            rules += [("global-hour", 3600, 1000)]
        # Do not create source/address records after global denial.
        for name, seconds, maximum in rules:
            if not await self._counter(db, f"{prefix}:{name}", seconds, maximum):
                return False
        rules = [(900, 30)] if reset else [(60, 10), (3600, 60)]
        for seconds, maximum in rules:
            if not await self._counter(
                db, f"{prefix}:{seconds}:" + self.key("source", source), seconds, maximum
            ):
                return False
        return True

    async def reset_limit(self, source):
        async with self.work() as work:
            allowed = await self.limit(work.session, source, reset=True)
            await work.commit()
        if not allowed:
            raise RecoveryLimited()

    async def request(self, email, locale, source):
        async with self.work() as work:
            db = work.session
            allowed = await self.limit(db, source)
            if not allowed:
                await work.commit()
                raise RecoveryLimited()
            key = self.key("address", email)
            cooldown = await self._counter(db, "address-minute:" + key, 60, 1)
            hourly = await self._counter(db, "address-hour:" + key, 3600, 3)
            if cooldown and hourly:
                await capacity(db, "password_recovery")
                await db.execute(
                    text("""INSERT INTO email_jobs(purpose,recipient,locale)
                    VALUES ('password_recovery',:email,:locale)"""),
                    {"email": email, "locale": locale},
                )
            await work.commit()

    async def claim(self):
        async with self.work() as work:
            await work.session.execute(
                text("""
              UPDATE email_jobs SET state='failed',failure_category='ambiguous',
                updated_at=clock_timestamp(),lease_owner=NULL,lease_expires_at=NULL
              WHERE id IN (SELECT id FROM email_jobs WHERE state='leased' AND attempts>=5
                AND lease_expires_at<=clock_timestamp() LIMIT 500 FOR UPDATE SKIP LOCKED)
            """)
            )
            row = (
                (
                    await work.session.execute(
                        text("""
              WITH candidate AS (SELECT id FROM email_jobs
                WHERE (state='pending' AND attempts<5 AND next_attempt_at<=clock_timestamp()
                  OR state='leased' AND attempts<5 AND lease_expires_at<=clock_timestamp())
                ORDER BY next_attempt_at,created_at FOR UPDATE SKIP LOCKED LIMIT 1)
              UPDATE email_jobs SET state='leased',attempts=LEAST(attempts+1,5),
                lease_owner=:lease,lease_expires_at=clock_timestamp()+interval '120 seconds',
                updated_at=clock_timestamp()
              WHERE id IN (SELECT id FROM candidate) RETURNING *
            """),
                        {"lease": uuid4()},
                    )
                )
                .mappings()
                .one_or_none()
            )
            await work.commit()
            return dict(row) if row else None

    async def finish(self, job_id, lease, state, category=None, delay=0):
        async with self.work() as work:
            result = await work.session.execute(
                text("""
              UPDATE email_jobs SET state=:state,failure_category=:category,
                next_attempt_at=clock_timestamp()+make_interval(secs=>:delay),
                lease_owner=NULL,lease_expires_at=NULL,updated_at=clock_timestamp()
              WHERE id=:id AND lease_owner=:lease AND state='leased'
                AND lease_expires_at>clock_timestamp()
            """),
                {
                    "id": job_id,
                    "lease": lease,
                    "state": state,
                    "category": category,
                    "delay": delay,
                },
            )
            await work.commit()
            return result.rowcount == 1

    async def cleanup(self):
        async with self.work() as work:
            await work.session.execute(
                text("""DELETE FROM auth_tokens WHERE id IN
              (SELECT id FROM auth_tokens WHERE purpose='reset_password'
               AND expires_at<clock_timestamp()-interval '7 days' LIMIT 500)""")
            )
            await work.session.execute(
                text("""DELETE FROM email_jobs WHERE id IN
              (SELECT id FROM email_jobs WHERE state IN ('accepted','failed','cancelled')
               AND updated_at<clock_timestamp()-interval '7 days'
               ORDER BY updated_at LIMIT 500)""")
            )
            await work.session.execute(
                text("""DELETE FROM recovery_limits WHERE id IN
              (SELECT id FROM recovery_limits WHERE expires_at<clock_timestamp()-interval '24 hours'
               LIMIT 500)""")
            )
            await work.commit()

    async def prepare(self, job, tokens, public_url):
        async with AuthUnitOfWork(self.work()) as work:
            db = work.work.session
            user = (
                (
                    await db.execute(
                        text("SELECT * FROM users WHERE email=:email FOR UPDATE"),
                        {"email": job["recipient"]},
                    )
                )
                .mappings()
                .one_or_none()
            )
            current = (
                (
                    await db.execute(
                        text("""SELECT * FROM email_jobs WHERE id=:id
                AND state='leased' AND lease_owner=:lease AND lease_expires_at>clock_timestamp()
                FOR UPDATE"""),
                        {"id": job["id"], "lease": job["lease_owner"]},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if not current:
                return None
            now = await db.scalar(text("SELECT clock_timestamp()"))
            if (
                not user
                or current["expires_at"] <= now
                or (
                    current["purpose"] == "password_recovery"
                    and user["password_changed_at"]
                    and current["created_at"] <= user["password_changed_at"]
                )
            ):
                await db.execute(
                    text(
                        "UPDATE email_jobs SET state='cancelled',updated_at=clock_timestamp(),"
                        "lease_owner=NULL,lease_expires_at=NULL WHERE id=:id"
                    ),
                    {"id": job["id"]},
                )
                await work.commit()
                return None
            if current["purpose"] == "password_changed":
                await work.commit()
                return (user["email"], None)
            if current["token_hash"]:
                await db.execute(
                    text("""UPDATE auth_tokens SET revoked_at=clock_timestamp()
                    WHERE user_id=:user AND purpose='reset_password' AND token_hash=:hash
                    AND used_at IS NULL AND revoked_at IS NULL"""),
                    {"user": user["id"], "hash": current["token_hash"]},
                )
            token = await tokens.issue_in_work(work, user["id"], "reset_password")
            await db.execute(
                text("UPDATE email_jobs SET user_id=:user,token_hash=:hash WHERE id=:id"),
                {"user": user["id"], "hash": digest(token.raw), "id": job["id"]},
            )
            await work.commit()
            return user[
                "email"
            ], f"{public_url}/reset-password#userId={user['id']}&token={token.raw}"
