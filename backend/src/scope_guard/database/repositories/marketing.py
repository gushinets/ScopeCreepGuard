"""One post-lock READ COMMITTED statement projects only analytics source facts."""

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from scope_guard.database.models.marketing import marketing_metrics
from scope_guard.domain.marketing import Snapshot

LOCK_KEY = 731486290617

# All subqueries share a statement snapshot. No email, text, document, prompt,
# response, or accounting reservation is copied into the analytics projection.
SOURCE_SQL = """
WITH owners AS MATERIALIZED (
 SELECT id,user_id,created_at AS registered_at FROM profiles WHERE NOT analytics_excluded
), runs AS MATERIALIZED (
 SELECT r.id,p.id AS profile_id,r.created_at,r.finished_at,r.status,
 CASE WHEN EXISTS(SELECT 1 FROM llm_operations o WHERE o.analysis_run_id=r.id AND o.kind='estimate')
   OR EXISTS(SELECT 1 FROM activity_events e WHERE e.analysis_run_id=r.id AND
     (e.event_type='estimate.requested' OR e.payload->>'purpose'='estimate'))
 THEN 'estimate' ELSE 'check' END AS kind
 FROM analysis_runs r JOIN projects j ON j.id=r.project_id
 JOIN owners p ON p.user_id=j.user_id
), saved AS MATERIALIZED (
 SELECT r.id,r.profile_id,min(h.completed_at) AS completed_at
 FROM runs r JOIN history_entries h ON h.analysis_run_id=r.id
 WHERE r.kind='check' AND r.status='succeeded' AND h.source_kind='explicit'
 AND h.completed_at IS NOT NULL GROUP BY r.id,r.profile_id
), checks AS (
 SELECT s.*,e.accuracy FROM saved s JOIN owners p ON p.id=s.profile_id
 LEFT JOIN evaluation_cases e ON e.analysis_run_id=s.id AND e.user_id=p.user_id
), durable AS MATERIALIZED (
 SELECT o.id,p.id AS profile_id,o.kind AS source_kind,
 CASE o.kind WHEN 'regenerate' THEN 'regeneration' WHEN 'translate' THEN 'translation'
 ELSE o.kind END AS kind,o.created_at,o.finished_at,o.status
 FROM llm_operations o JOIN owners p ON p.user_id=o.owner_id
), fallback_runs AS (
 SELECT r.id,r.profile_id,r.kind,r.created_at,
 CASE WHEN r.kind='check' AND r.status='succeeded'
 THEN s.completed_at ELSE r.finished_at END AS finished_at,
 CASE WHEN r.kind='check' AND r.status='succeeded' AND s.id IS NULL
 THEN 'pending' ELSE r.status END AS status
 FROM runs r LEFT JOIN saved s ON s.id=r.id
 WHERE NOT EXISTS(SELECT 1 FROM llm_operations o
 WHERE o.analysis_run_id=r.id AND o.kind IN ('check','estimate'))
), fallback_events AS (
 SELECT e.operation_id AS id,p.id AS profile_id,e.project_id,
 CASE WHEN e.event_type LIKE 'reply.%' THEN 'regeneration' ELSE 'translation' END AS kind,
 min(coalesce(e.occurred_at,e.created_at))
 FILTER(WHERE e.event_type LIKE '%.requested') AS created_at,
 max(coalesce(e.occurred_at,e.created_at))
 FILTER(WHERE e.event_type NOT LIKE '%.requested') AS finished_at,
 CASE WHEN bool_or(e.event_type IN ('reply.regenerated','translation.completed')) THEN 'succeeded'
 WHEN bool_or(e.event_type LIKE '%.failed') THEN 'failed'
 WHEN bool_or(e.event_type LIKE '%.cancelled') THEN 'cancelled' ELSE 'pending' END AS status
 FROM activity_events e JOIN projects j ON j.id=e.project_id JOIN owners p ON p.user_id=j.user_id
 WHERE e.event_type IN ('reply.requested','reply.regenerated','reply.failed','reply.cancelled',
 'translation.requested','translation.completed','translation.failed','translation.cancelled')
 AND NOT EXISTS(SELECT 1 FROM llm_operations o
 WHERE o.project_id=e.project_id AND o.command_key=e.operation_id)
 GROUP BY e.project_id,e.operation_id,p.id,
 CASE WHEN e.event_type LIKE 'reply.%' THEN 'regeneration' ELSE 'translation' END
), legacy_generations AS (
 SELECT r.operation_id AS id,p.id AS profile_id,
 CASE r.reason WHEN 'regenerate' THEN 'regeneration' ELSE 'translation' END AS kind,
 NULL::timestamptz AS created_at,r.created_at AS finished_at,'succeeded' AS status
 FROM draft_revisions r JOIN projects j ON j.id=r.project_id
 JOIN owners p ON p.user_id=j.user_id
 WHERE r.reason IN ('regenerate','language_change')
 AND NOT EXISTS(SELECT 1 FROM activity_events e
 WHERE e.draft_revision_id=r.id AND e.event_version IS NOT NULL)
 AND NOT EXISTS(SELECT 1 FROM llm_operations o
 WHERE o.project_id=r.project_id AND (o.command_key=r.operation_id
 OR (o.status='succeeded' AND o.result#>>'{draft,id}'=r.draft_id::text
 AND o.result#>>'{draft,revision}'=r.revision::text)))
 AND NOT EXISTS(SELECT 1 FROM fallback_events e
 WHERE e.id=r.operation_id AND e.project_id=r.project_id)
), operations AS (
 SELECT id,profile_id,kind,created_at,finished_at,status FROM durable
 WHERE source_kind<>'diagnostic'
 UNION ALL SELECT * FROM fallback_runs
 UNION ALL SELECT id,profile_id,kind,created_at,finished_at,status FROM fallback_events
 UNION ALL SELECT * FROM legacy_generations
), orders AS (
 SELECT c.id,p.id AS profile_id,c.finalized_at,c.voided_at FROM change_orders c
 JOIN projects j ON j.id=c.project_id JOIN owners p ON p.user_id=j.user_id
), calls AS (
 SELECT c.id,d.profile_id,c.started_at,c.semantic_attempt,c.transport_attempt,
 c.input_tokens,c.output_tokens,c.cached_tokens,c.reasoning_tokens,
 c.estimated_cost::text AS estimated_cost,c.validation_status
 FROM provider_calls c JOIN durable d ON d.id=c.operation_id
)
SELECT statement_timestamp() AS cutoff,
 (SELECT coalesce(jsonb_agg(jsonb_build_object('id',id,'registered_at',registered_at)),'[]')
 FROM owners) AS profiles,
 (SELECT coalesce(jsonb_agg(to_jsonb(c)),'[]') FROM checks c) AS checks,
 (SELECT coalesce(jsonb_agg(to_jsonb(o)),'[]') FROM operations o) AS operations,
 (SELECT coalesce(jsonb_agg(to_jsonb(o)),'[]') FROM orders o) AS orders,
 (SELECT coalesce(jsonb_agg(to_jsonb(c)),'[]') FROM calls c) AS calls,
 EXISTS(SELECT 1 FROM history_entries h JOIN projects j ON j.id=h.project_id
 JOIN owners p ON p.user_id=j.user_id WHERE h.source_kind='legacy_unverified') AS legacy_history,
 (SELECT min(report_date) FROM marketing_metrics) AS earliest_report
"""


class MarketingRepository:
    def __init__(self, session):
        self.session = session

    async def snapshot(self) -> tuple[Snapshot, date | None] | None:
        # Must precede ANY reads; a waiting REPEATABLE READ transaction would retain
        # a stale pre-lock snapshot. Explicitly keep this UoW READ COMMITTED.
        await self.session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY})
        if not await self.session.scalar(
            text("SELECT to_regclass('public.marketing_metrics') IS NOT NULL")
        ):
            return None  # Explicit pre-0006 compatibility: no invented metrics.
        record = (await self.session.execute(text(SOURCE_SQL))).mappings().one()
        return Snapshot(
            **{
                key: record[key]
                for key in (
                    "cutoff",
                    "profiles",
                    "checks",
                    "operations",
                    "orders",
                    "calls",
                    "legacy_history",
                )
            }
        ), record["earliest_report"]

    async def save(self, rows: list[dict]) -> None:
        # DB wall clock is after the snapshot even after a long advisory-lock wait.
        calculated = await self.session.scalar(text("SELECT clock_timestamp()"))
        for row in rows:
            statement = insert(marketing_metrics).values(**row, calculated_at=calculated)
            await self.session.execute(
                statement.on_conflict_do_update(
                    index_elements=[marketing_metrics.c.report_date],
                    set_={
                        column.name: statement.excluded[column.name]
                        for column in marketing_metrics.c
                        if column.name != "report_date"
                    },
                    where=marketing_metrics.c.data_through <= statement.excluded.data_through,
                )
            )

    async def read(self, start: date, end: date) -> list[dict]:
        rows = await self.session.execute(
            select(marketing_metrics)
            .where(marketing_metrics.c.report_date >= start, marketing_metrics.c.report_date < end)
            .order_by(marketing_metrics.c.report_date)
        )
        return [dict(row) for row in rows.mappings()]
