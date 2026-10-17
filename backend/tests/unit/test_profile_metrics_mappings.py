def test_supported_mappings_have_current_columns_and_no_retired_draft_fields():
    from scope_guard.database.models.activity import activity_events
    from scope_guard.database.models.marketing import marketing_metrics
    from scope_guard.database.models.profiles import profiles
    from scope_guard.database.models.workflow import WORKFLOW_METADATA

    assert "history_entry_id" not in WORKFLOW_METADATA.tables["drafts"].c
    assert "revision" in WORKFLOW_METADATA.tables["drafts"].c
    assert "check_snapshot" in WORKFLOW_METADATA.tables["history_entries"].c
    assert "profile_id" in WORKFLOW_METADATA.tables["projects"].c
    assert profiles.c.user_id.nullable is False
    assert activity_events.c.project_id.nullable is True
    assert marketing_metrics.c.ai_calls.nullable is True
    assert marketing_metrics.c.ai_estimated_cost_usd.type.scale == 10
    assert "pdf_exports" not in marketing_metrics.c
    assert marketing_metrics.c.dau.nullable is True
    assert marketing_metrics.c.check_duration_p95_ms.type.precision == 20
    assert marketing_metrics.c.check_success_percent.type.scale == 4
