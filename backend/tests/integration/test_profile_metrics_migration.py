"""Profile migration checks against owned disposable PostgreSQL only."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from scope_guard.database.migrations import migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration


def test_populated_upgrade_preserves_history_and_events_and_backfill_is_repeatable(disposable_url):
    from scope_guard.database.profile_backfill import backfill_profiles

    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.begin() as connection:
            migrate(connection, target="0005_llm_workflow")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            owner = connection.exec_driver_sql(
                "INSERT INTO users(email,password_hash,created_at) VALUES "
                "('owner@example.test','synthetic','2020-01-02Z') RETURNING id"
            ).scalar_one()
            project = connection.execute(
                text(
                    "INSERT INTO projects(user_id,name,industry,scope,updated_at) "
                    "VALUES(:owner,'Old','Development','scope',now()) RETURNING id"
                ),
                {"owner": owner},
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO history_entries(project_id,date,request,verdict,summary,"
                    "check_snapshot,schema_version,source_kind) VALUES(:project,'2020-01-03',"
                    "'old request','in_scope','old summary','{}',1,'legacy_unverified')"
                ),
                {"project": project},
            )
            connection.execute(
                text(
                    "INSERT INTO activity_events(project_id,actor_type,actor_user_id,event_type,"
                    "operation_id,payload,payload_version) VALUES(:project,'user',:owner,"
                    "'legacy.event',gen_random_uuid(),jsonb_build_object('retained',true),1)"
                ),
                {"project": project, "owner": owner},
            )
            old_history = connection.exec_driver_sql(
                "SELECT to_jsonb(h) FROM history_entries h"
            ).scalar_one()
            old_event = connection.exec_driver_sql(
                "SELECT to_jsonb(e) FROM activity_events e"
            ).scalar_one()
            migrate(connection, target="head")
            revisions = (
                connection.exec_driver_sql(
                    "SELECT to_jsonb(r) FROM profile_revisions r ORDER BY id"
                )
                .scalars()
                .all()
            )
            backfill_profiles(connection)
            backfill_profiles(connection)
            assert (
                connection.exec_driver_sql(
                    "SELECT to_jsonb(r) FROM profile_revisions r ORDER BY id"
                )
                .scalars()
                .all()
                == revisions
            )
            assert (
                connection.exec_driver_sql("SELECT to_jsonb(h) FROM history_entries h").scalar_one()
                == old_history
            )
            new_event = connection.exec_driver_sql(
                "SELECT to_jsonb(e) FROM activity_events e"
            ).scalar_one()
            assert {key: new_event[key] for key in old_event} == old_event
            assert all(value is None for key, value in new_event.items() if key not in old_event)
            assert connection.exec_driver_sql("SELECT count(*) FROM profiles").scalar_one() == 1
            assert connection.exec_driver_sql(
                "SELECT p.created_at=u.created_at AND p.id=j.profile_id "
                "FROM profiles p JOIN users u ON u.id=p.user_id JOIN projects j ON j.user_id=u.id"
            ).scalar_one()
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.exec_driver_sql("UPDATE activity_events SET payload='{}'")
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.exec_driver_sql("DELETE FROM profile_revisions")
            migrate(connection, target="head")
    finally:
        engine.dispose()


def test_empty_upgrade_enforces_ownership_contracts_and_nullable_metrics(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.begin() as connection:
            migrate(connection, target="head")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            for email in ("one", "two"):
                connection.exec_driver_sql(
                    f"INSERT INTO users(email,password_hash) VALUES('{email}','synthetic')"
                )
            from scope_guard.database.profile_backfill import backfill_profiles

            backfill_profiles(connection)
            first, second = connection.exec_driver_sql(
                "SELECT id,user_id FROM profiles ORDER BY id"
            ).all()
            project = connection.execute(
                text(
                    "INSERT INTO projects(user_id,profile_id,name,industry,scope,updated_at) "
                    "VALUES(:user,:profile,'New','Development','scope',now()) RETURNING id"
                ),
                {"user": first.user_id, "profile": first.id},
            ).scalar_one()
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("UPDATE projects SET profile_id=:id"), {"id": second.id})
            event = {
                "profile": first.id,
                "user": first.user_id,
                "project": project,
                "key": "created/1",
                "operation": uuid4(),
            }
            statement = text(
                "INSERT INTO activity_events(profile_id,project_id,actor_type,actor_user_id,"
                "event_type,operation_id,payload,payload_version,event_version,source,"
                "deduplication_key,occurred_at,recorded_at) VALUES(:profile,:project,'user',:user,"
                "'profile.created',:operation,'{}',1,2,'app',:key,now(),now())"
            )
            connection.execute(statement, event | {"project": None})
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(statement, event | {"project": None})
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(statement, event | {"profile": second.id, "key": "bad"})
            # A source key, not project/operation/type, identifies new-version attempts.
            connection.execute(statement, event | {"key": "project/1"})
            connection.execute(statement, event | {"key": "project/2"})
            for original, replacement in (
                ("'{}',1,2", "'[]',1,2"),
                ("'{}',1,2", "'{}',0,2"),
                ("'{}',1,2", "'{}',1,3"),
                ("'app'", "''"),
                ("now(),now()", "now(),now()-interval '1 second'"),
                ("'user',:user", "'user',NULL"),
            ):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(
                        text(str(statement).replace(original, replacement)),
                        event | {"key": "invalid"},
                    )
            session = connection.execute(
                text(
                    "INSERT INTO product_sessions(profile_id,browser_key_hash,started_at,"
                    "last_activity_at,rule_version) VALUES(:profile,:browser,now(),now(),1) "
                    "RETURNING id"
                ),
                {"profile": second.id, "browser": "a" * 64},
            ).scalar_one()
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO activity_events(profile_id,product_session_id,actor_type,"
                        "actor_user_id,event_type,operation_id,payload,payload_version,event_version,"
                        "source,deduplication_key,occurred_at,recorded_at) "
                        "VALUES(:profile,:session,"
                        "'user',:user,'profile.updated',gen_random_uuid(),'{}',1,2,'app','session',"
                        "now(),now())"
                    ),
                    {"profile": first.id, "user": first.user_id, "session": session},
                )
            for sql in (
                "UPDATE profiles SET revision=0",
                "UPDATE profiles SET updated_at=created_at-interval '1 second'",
                "UPDATE profile_preferences SET preferred_tone='unrecognized'",
                "UPDATE profile_preferences SET timezone='unknown/zone'",
                "UPDATE profile_preferences SET locale='invalid'",
                "UPDATE profile_preferences SET default_currency='INVALID'",
                "UPDATE product_sessions SET last_activity_at=started_at-interval '1 second'",
                "UPDATE product_sessions SET ended_at=last_activity_at-interval '1 second'",
                "INSERT INTO product_sessions(profile_id,browser_key_hash,started_at,"
                "last_activity_at,rule_version) SELECT profile_id,browser_key_hash,now(),now(),1 "
                "FROM product_sessions",
            ):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.exec_driver_sql(sql)
            connection.exec_driver_sql(
                "INSERT INTO marketing_metrics(report_date,calculated_at,data_through,"
                "definition_version,is_partial,quality_notes) "
                "VALUES('2026-10-16',now(),now(),1,true,'[]')"
            )
            assert connection.exec_driver_sql("SELECT dau FROM marketing_metrics").scalar() is None
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.exec_driver_sql("UPDATE marketing_metrics SET dau=-1")
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.exec_driver_sql("UPDATE marketing_metrics SET stickiness_percent=101")
    finally:
        engine.dispose()


def test_current_runtime_catalog_checks_drift_and_mapping_contract(disposable_url):
    from scope_guard.database.models.workflow import WORKFLOW_METADATA
    from scope_guard.database.schema_verification import (
        SchemaCompatibilityError,
        inspect_profile_schema,
        verify_llm_schema,
    )

    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.begin() as connection:
            migrate(connection, target="0005_llm_workflow")
            verify_llm_schema(connection)
            migrate(connection, target="head")
            verify_llm_schema(connection)
            catalog = inspect_profile_schema(connection)
            for name, table in catalog["tables"].items():
                assert set(WORKFLOW_METADATA.tables[name].c.keys()) == {
                    column["name"] for column in table["columns"]
                }
                for column in table["columns"]:
                    mapped = WORKFLOW_METADATA.tables[name].c[column["name"]]
                    assert mapped.nullable == (not column["not_null"])
            for sql in (
                "ALTER TABLE activity_events DISABLE TRIGGER immutable_events",
                "ALTER TABLE projects DROP CONSTRAINT projects_profile_owner_fk",
                "ALTER TABLE marketing_metrics DROP COLUMN dau",
            ):
                with pytest.raises(SchemaCompatibilityError), connection.begin_nested():
                    connection.exec_driver_sql(sql)
                    verify_llm_schema(connection)
            verify_llm_schema(connection)
    finally:
        engine.dispose()


def test_supported_history_read_does_not_join_retired_draft_columns(disposable_url):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from scope_guard.database.queries.history import HistoryQueries

    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.begin() as connection:
            migrate(connection, target="head")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            owner = connection.exec_driver_sql(
                "INSERT INTO users(email,password_hash) VALUES('history','synthetic') RETURNING id"
            ).scalar_one()
            project = connection.execute(
                text(
                    "INSERT INTO projects(user_id,name,industry,scope,updated_at) "
                    "VALUES(:owner,'History','Development','scope',now()) RETURNING id"
                ),
                {"owner": owner},
            ).scalar_one()
            history = connection.execute(
                text(
                    "INSERT INTO history_entries(project_id,date,request,verdict,summary,"
                    "check_snapshot,schema_version,source_kind) VALUES(:project,'2020-01-03',"
                    "'old request','in_scope','old summary','{}',1,'legacy_unverified') "
                    "RETURNING id"
                ),
                {"project": project},
            ).scalar_one()

        async def read():
            async_engine = create_async_engine(normalize_url(disposable_url))
            try:
                async with async_sessionmaker(async_engine)() as session:
                    result = await HistoryQueries(session).for_projects((project,))
                    assert len(result) == 1
                    assert result[0].id == history
                    assert result[0].draft_id is None
                    assert result[0].summary == "old summary"
            finally:
                await async_engine.dispose()

        asyncio.run(read())
    finally:
        engine.dispose()
