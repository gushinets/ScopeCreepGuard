"""Server-clock browser sessions. Only explicit interaction calls touch inactivity."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from scope_guard.services.activity.context import browser_key


class ProductSessions:
    def __init__(self, session):
        self.session = session

    async def resolve(self, profile, browser_hash=None, *, touch=True, now=None):
        browser_hash = browser_hash or browser_key.get()
        if browser_hash is None:
            return None
        import re

        if not re.fullmatch("[a-f0-9]{64}", browser_hash):
            raise ValueError("invalid_browser_identity")
        now = now or datetime.now(UTC)
        await self.session.execute(
            text("SELECT id FROM profiles WHERE id=:id FOR UPDATE"), {"id": profile}
        )
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT * FROM product_sessions WHERE profile_id=:profile AND "
                        "browser_key_hash=:browser AND ended_at IS NULL"
                    ),
                    {"profile": profile, "browser": browser_hash},
                )
            )
            .mappings()
            .first()
        )
        if row and now < row["last_activity_at"] + timedelta(minutes=30):
            if touch:
                await self.session.execute(
                    text(
                        "UPDATE product_sessions SET "
                        "last_activity_at=greatest(last_activity_at,:now) "
                        "WHERE id=:id"
                    ),
                    {"now": now, "id": row["id"]},
                )
            return row["id"]
        if not touch:
            return None
        if row:
            await self.session.execute(
                text(
                    "UPDATE product_sessions SET ended_at=last_activity_at + interval '30 minutes' "
                    "WHERE id=:id"
                ),
                {"id": row["id"]},
            )
        identifier = await self.session.scalar(
            text(
                "INSERT INTO product_sessions(profile_id,browser_key_hash,started_at,"
                "last_activity_at,rule_version) VALUES(:profile,:browser,:now,:now,1) RETURNING id"
            ),
            {"profile": profile, "browser": browser_hash, "now": now},
        )
        return identifier
