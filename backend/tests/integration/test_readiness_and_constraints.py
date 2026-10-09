import asyncio
import json
import time

import httpx
import pytest
from integration.support import ROOT, docker, migration_digest, replay_drizzle
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def test_reference_provenance_matches_committed_journal():
    reference = json.loads(
        (ROOT / "backend/src/scope_guard/infrastructure/database/baseline_schema.json").read_text()
    )
    journal = json.loads((ROOT / "frontend/drizzle/meta/_journal.json").read_text())
    assert reference["drizzle_hash_normalization"] == "CRLF to LF"
    assert reference["drizzle"] == [
        {
            "tag": item["tag"],
            "when": item["when"],
            "sha256": migration_digest(
                (ROOT / "frontend/drizzle" / (item["tag"] + ".sql")).read_bytes()
            ),
        }
        for item in journal["entries"]
    ]


def test_ready_recovers_and_uow_returns_failed_connections(disposable_url, postgres_server):
    from scope_guard.core.config import Settings
    from scope_guard.main import create_app

    replay_drizzle(disposable_url)

    async def exercise():
        app = create_app(Settings(_env_file=None, database_url=disposable_url))
        async with app.router.lifespan_context(app):
            database = app.state.database
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                assert (await client.get("/health/ready")).status_code == 200
                docker("pause", postgres_server.container_id)
                try:
                    started = time.monotonic()
                    assert (await client.get("/health/ready")).status_code == 503
                    assert time.monotonic() - started < 4.5
                    assert (await client.get("/health/live")).status_code == 200
                finally:
                    docker("unpause", postgres_server.container_id)
                assert (await client.get("/health/ready")).status_code == 200
                async with database.new_uow() as uow:
                    await uow.session.execute(
                        text("INSERT INTO users(email,password_hash) VALUES ('same@test','hash')")
                    )
                    await uow.commit()
                with pytest.raises(IntegrityError):
                    async with database.new_uow() as uow:
                        await uow.session.execute(
                            text(
                                "INSERT INTO users(email,password_hash) VALUES ('same@test','hash')"
                            )
                        )
                        await uow.commit()
                async with database.new_uow() as first, database.new_uow() as second:
                    assert first.session is not second.session
                    await first.session.execute(text("SELECT 1"))
                    await second.session.execute(text("SELECT 1"))
                assert (await client.get("/health/ready")).json() == {
                    "status": "ok",
                    "database": "ok",
                }
                assert database.engine.pool.checkedout() == 0

    asyncio.run(exercise())


def test_constraints_and_project_deletion_cascades(disposable_url):
    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with engine.begin() as connection:
            user = connection.exec_driver_sql(
                "INSERT INTO users(email,password_hash) VALUES ('owner@test','hash') RETURNING id"
            ).scalar()
            project = connection.execute(
                text(
                    "INSERT INTO projects(user_id,name,industry,scope) VALUES "
                    "(:user,'Website','Development','Scope') RETURNING id"
                ),
                {"user": user},
            ).scalar()
            history = connection.execute(
                text(
                    "INSERT INTO history_entries(project_id,date,request,verdict,summary) "
                    "VALUES (:project,'2026-10-09','Extra','out_of_scope','Extra') "
                    "RETURNING id"
                ),
                {"project": project},
            ).scalar()
            connection.execute(
                text(
                    "INSERT INTO "
                    "drafts(project_id,history_entry_id,idempotency_key,analysis_snapshot,"
                    "draft_document,locale,client_material_language) "
                    "VALUES (:project,:history,gen_random_uuid(),'{}','{}','en','en')"
                ),
                {"project": project, "history": history},
            )
            for linked in (history, None):
                connection.execute(
                    text(
                        "INSERT INTO "
                        "evaluation_cases(user_id,history_entry_id,scope,request,ai_verdict,"
                        "ai_reasoning,accuracy,industry) "
                        "VALUES "
                        "(:user,:history,'Scope','Extra','out_of_scope','Reason','debatable','Development')"
                    ),
                    {"user": user, "history": linked},
                )
            for statement in (
                "UPDATE projects SET "
                "start_date='2026-01-01',pricing_model='hourly',currency='USD',hourly_rate=-1",
                "UPDATE drafts SET status='published'",
                "UPDATE drafts SET locale='fr'",
                "UPDATE evaluation_cases SET accuracy='correct'",
            ):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.exec_driver_sql(statement)
            connection.execute(text("DELETE FROM projects WHERE id=:id"), {"id": project})
            for table in ("history_entries", "drafts"):
                assert connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar() == 0
            assert connection.exec_driver_sql("SELECT count(*) FROM evaluation_cases").scalar() == 1
            connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": user})
            assert connection.exec_driver_sql("SELECT count(*) FROM evaluation_cases").scalar() == 0
    finally:
        engine.dispose()
