from decimal import Decimal

import pytest
from integration.support import replay_drizzle
from sqlalchemy import create_engine, select

pytestmark = pytest.mark.integration


def test_mapped_rows_round_trip_decimals_json_and_server_defaults(disposable_url):
    from sqlalchemy.orm import Session

    from scope_guard.infrastructure.database.models import (
        DraftRow,
        HistoryEntryRow,
        ProjectRow,
        UserRow,
    )

    replay_drizzle(disposable_url)
    engine = create_engine(disposable_url.replace("postgresql://", "postgresql+psycopg://"))
    try:
        with Session(engine) as session:
            user = UserRow(email="owner@example.test", password_hash="synthetic")
            session.add(user)
            session.flush()
            project = ProjectRow(
                user_id=user.id,
                name="Website",
                industry="Development",
                scope="Five pages",
                start_date=None,
            )
            session.add(project)
            session.flush()
            history = HistoryEntryRow(
                project_id=project.id,
                date="2026-10-09",
                request="Extra",
                verdict="out_of_scope",
                summary="Extra",
            )
            session.add(history)
            session.flush()
            from uuid import uuid4

            draft = DraftRow(
                project_id=project.id,
                history_entry_id=history.id,
                idempotency_key=uuid4(),
                analysis_snapshot={"private": "Русский"},
                draft_document={"version": 1},
                locale="en",
                client_material_language="es",
            )
            session.add(draft)
            session.commit()
            assert user.id is not None
            assert user.created_at.tzinfo is not None
            assert draft.project_snapshot is None
            assert draft.analysis_snapshot == {"private": "Русский"}
            assert session.scalar(select(ProjectRow)).hourly_rate is None
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE projects SET start_date='2026-01-01', pricing_model='hourly', "
                "currency='USD', hourly_rate=125.10"
            )
        with Session(engine) as session:
            assert session.scalar(select(ProjectRow)).hourly_rate == Decimal("125.10")
    finally:
        engine.dispose()
