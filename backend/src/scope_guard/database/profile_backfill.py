"""Explicit, transactional ownership backfill; never called by application startup."""

from sqlalchemy.engine import Connection


def verify_profile_ownership(connection: Connection) -> None:
    """Fail closed on missing profiles, fabricated registration dates or wrong owners."""
    invalid = connection.exec_driver_sql("""
        SELECT EXISTS (
          SELECT 1 FROM public.users u LEFT JOIN public.profiles p ON p.user_id=u.id
          WHERE p.id IS NULL OR p.created_at IS DISTINCT FROM u.created_at
        ) OR EXISTS (
          SELECT 1 FROM public.projects j LEFT JOIN public.profiles p ON p.id=j.profile_id
          WHERE p.id IS NULL OR p.user_id IS DISTINCT FROM j.user_id
        )
    """).scalar_one()
    if invalid:
        raise RuntimeError("profile_ownership_backfill_verification_failed")


def backfill_profiles(connection: Connection) -> None:
    """Create only missing profiles and fill NULL project ownership, under table locks.

    Caller owns the transaction. Existing non-NULL ownership is never repaired silently.
    No legacy event, history, revision, UUID or user data is rewritten. Run explicitly
    again before closing the nullable project-owner rollout window.
    """
    connection.exec_driver_sql(
        "LOCK TABLE public.users,public.profiles,public.projects IN SHARE ROW EXCLUSIVE MODE"
    )
    if connection.exec_driver_sql("""
        SELECT EXISTS(SELECT 1 FROM public.projects j
          LEFT JOIN public.profiles p ON p.id=j.profile_id
          WHERE j.profile_id IS NOT NULL AND (p.id IS NULL OR p.user_id<>j.user_id))
    """).scalar_one():
        raise RuntimeError("profile_ownership_backfill_conflict")
    connection.exec_driver_sql("""
        WITH inserted AS (
          INSERT INTO public.profiles(user_id,created_at,updated_at)
          SELECT u.id,u.created_at,u.created_at FROM public.users u
          WHERE NOT EXISTS(SELECT 1 FROM public.profiles p WHERE p.user_id=u.id)
          RETURNING *
        )
        INSERT INTO public.profile_revisions(profile_id,revision,snapshot,actor_user_id,
          operation_id,created_at)
        SELECT i.id,i.revision,to_jsonb(i),i.user_id,i.id,i.created_at FROM inserted i;
        INSERT INTO public.profile_preferences(profile_id,updated_at)
          SELECT p.id,p.created_at FROM public.profiles p
          ON CONFLICT(profile_id) DO NOTHING;
        UPDATE public.projects j SET profile_id=p.id FROM public.profiles p
          WHERE j.user_id=p.user_id AND j.profile_id IS NULL;
    """)
    verify_profile_ownership(connection)
