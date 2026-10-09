from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


def test_metadata_preserves_all_tables_and_commercial_storage():
    from scope_guard.infrastructure.database.models import Base, ProjectRow

    assert set(Base.metadata.tables) == {
        "users",
        "projects",
        "history_entries",
        "drafts",
        "evaluation_cases",
    }
    ddl = str(CreateTable(ProjectRow.__table__).compile(dialect=postgresql.dialect()))
    assert "NUMERIC(14, 2)" in ddl
    assert "projects_commercial_terms_consistent" in ddl
    assert "end_date" not in ddl
    assert "client_email" not in ddl


def test_metadata_uses_database_enum_values_and_preserves_cascades():
    from scope_guard.infrastructure.database.models import DraftRow, EvaluationCaseRow

    accuracy = EvaluationCaseRow.__table__.c.accuracy.type
    assert accuracy.enums == ["correct", "wrong", "debatable"]
    fk = next(iter(EvaluationCaseRow.__table__.c.history_entry_id.foreign_keys))
    assert fk.ondelete == "CASCADE"
    assert fk.name == "evaluation_cases_history_entry_id_history_entries_id_fk"
    indexes = {index.name: index for index in DraftRow.__table__.indexes}
    assert indexes["drafts_project_creation_key_unique"].unique
    assert [c.name for c in indexes["drafts_project_created_at_idx"].columns] == [
        "project_id",
        "created_at",
    ]
