"""Profile changes, revision receipt and confirmed event share the caller's T1."""

import json

from sqlalchemy import text

from scope_guard.database.repositories.activity import EventRepository, profiles_supported
from scope_guard.database.repositories.sessions import ProductSessions
from scope_guard.domain.activity import ActivityEvent
from scope_guard.domain.drafts.workflow import WorkflowError, operation_hash
from scope_guard.domain.profiles import PREFERENCE_FIELDS, PROFILE_FIELDS, validate_changes


class Profiles:
    def __init__(self, session):
        self.session = session

    async def onboarding(self, owner, event=None):
        from scope_guard.domain.profiles.onboarding import transition

        supported = await self.session.scalar(
            text(
                "SELECT count(*)=2 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='profiles' "
                "AND column_name IN ('onboarding_status','onboarding_step')"
            )
        )
        if not supported:
            raise WorkflowError("profileUnavailable", 503)
        row = (
            await self.session.execute(
                text(
                    "SELECT onboarding_status,onboarding_step FROM profiles WHERE user_id=:owner"
                    + (" FOR UPDATE" if event else "")
                ),
                {"owner": owner},
            )
        ).one_or_none()
        if row is None:
            raise WorkflowError("profileNotFound", 404)
        status, step = row
        if event is not None:
            status, step = transition(status, step, event)
            await self.session.execute(
                text(
                    "UPDATE profiles SET onboarding_status=:status,onboarding_step=:step "
                    "WHERE user_id=:owner"
                ),
                {"owner": owner, "status": status, "step": step},
            )
        return {"status": status, "step": step}

    async def get(self, owner, *, lock=False):
        if not await profiles_supported(self.session):
            raise WorkflowError("profileUnavailable", 503)
        row = await self.session.scalar(
            text(
                "SELECT to_jsonb(p) FROM profiles p WHERE user_id=:owner"
                + (" FOR UPDATE" if lock else "")
            ),
            {"owner": owner},
        )
        if row is None:
            raise WorkflowError("profileNotFound", 404)
        preferences = await self.session.scalar(
            text("SELECT to_jsonb(p) FROM profile_preferences p WHERE profile_id=:id"),
            {"id": row["id"]},
        )
        return {
            "id": row["id"],
            "revision": str(row["revision"]),
            **{wire: row[column] for wire, column in PROFILE_FIELDS.items()},
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "preferences": {
                wire: preferences[column] for wire, column in PREFERENCE_FIELDS.items()
            },
        }

    async def create(self, owner):
        row = await self.session.scalar(
            text(
                "INSERT INTO profiles(user_id,created_at,updated_at) SELECT "
                "id,created_at,created_at "
                "FROM users WHERE id=:owner RETURNING id"
            ),
            {"owner": owner},
        )
        await self.session.execute(
            text("INSERT INTO profile_preferences(profile_id) VALUES(:id)"), {"id": row}
        )
        profile = await self.get(owner)
        await self.revision(owner, row, row, profile, None)
        await EventRepository(self.session).append(
            ActivityEvent(
                profile_id=row,
                operation_id=row,
                event_type="profile.created",
                source="profile",
                deduplication_key=f"{row}:created",
                actor_user_id=owner,
                payload={"revision": "1"},
            ),
            touch_session=True,
        )
        return profile

    async def revision(self, owner, profile, operation, snapshot, request_hash):
        await self.session.execute(
            text(
                "INSERT INTO "
                "profile_revisions(profile_id,revision,snapshot,actor_user_id,operation_id) "
                "VALUES(:profile,:revision,CAST(:snapshot AS jsonb),:owner,:operation)"
            ),
            {
                "profile": profile,
                "revision": int(snapshot["revision"]),
                "snapshot": json.dumps({"profile": snapshot, "requestHash": request_hash}),
                "owner": owner,
                "operation": operation,
            },
        )

    async def update(self, owner, expected, operation, changes):
        validate_changes(changes)
        current = await self.get(owner, lock=True)
        digest = operation_hash({"expectedRevision": str(expected), "changes": changes})
        prior = await self.session.scalar(
            text(
                "SELECT snapshot FROM profile_revisions WHERE profile_id=:id AND "
                "operation_id=:operation"
            ),
            {"id": current["id"], "operation": operation},
        )
        if prior:
            if prior.get("requestHash") != digest:
                raise WorkflowError("operationMismatch", 409)
            return prior["profile"]
        if int(current["revision"]) != expected:
            raise WorkflowError("profileConflict", 409)
        values = {
            column: changes[wire] for wire, column in PROFILE_FIELDS.items() if wire in changes
        }
        assignments = [f"{column}=:{column}" for column in values]
        await self.session.execute(
            text(
                "UPDATE profiles SET "
                + ",".join(assignments + ["revision=revision+1", "updated_at=now()"])
                + " WHERE id=:id"
            ),
            {**values, "id": current["id"]},
        )
        preferences = changes.get("preferences", {})
        if preferences:
            values = {PREFERENCE_FIELDS[k]: v for k, v in preferences.items()}
            await self.session.execute(
                text(
                    "UPDATE profile_preferences SET "
                    + ",".join(
                        [f"{k}=:{k}" for k in values] + ["revision=revision+1", "updated_at=now()"]
                    )
                    + " WHERE profile_id=:id"
                ),
                {**values, "id": current["id"]},
            )
        result = await self.get(owner)
        await self.revision(owner, current["id"], operation, result, digest)
        await EventRepository(self.session).append(
            ActivityEvent(
                profile_id=current["id"],
                operation_id=operation,
                event_type="profile.updated",
                source="profile",
                deduplication_key=f"{current['id']}:{operation}:updated",
                actor_user_id=owner,
                payload={"revision": result["revision"], "changedFields": sorted(changes)},
            ),
            touch_session=True,
        )
        return result

    async def observe(self, owner):
        if not await profiles_supported(self.session):
            return None  # Authentication retains its explicit pre-0006 compatibility path.
        profile = await self.get(owner, lock=True)
        return await ProductSessions(self.session).resolve(profile["id"])


class ProfilesUnitOfWork:
    def __init__(self, work):
        self.work = work

    async def __aenter__(self):
        await self.work.__aenter__()
        self.profiles = Profiles(self.work.session)
        return self

    async def __aexit__(self, *args):
        await self.work.__aexit__(*args)

    async def commit(self):
        await self.work.commit()
