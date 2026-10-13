"""Tighten only after per-record lossless transfer verification."""

from alembic import op

revision = "0003_workflow_constraints"
down_revision = "0002_workflow_expand"
branch_labels = depends_on = None


def upgrade():
    from scope_guard.database.workflow_backfill import retire_verified_legacy_rows

    retire_verified_legacy_rows(op.get_bind())
    op.execute("""
    ALTER TABLE drafts ALTER COLUMN request_text SET NOT NULL,
     ALTER COLUMN analysis_is_stale SET NOT NULL, ALTER COLUMN revision SET NOT NULL,
     ADD CONSTRAINT drafts_one_per_project UNIQUE(project_id),
     ADD CONSTRAINT drafts_positive_revision CHECK(revision>0);
    ALTER TABLE projects ALTER COLUMN updated_at SET NOT NULL;
    ALTER TABLE history_entries ALTER COLUMN check_snapshot SET NOT NULL,
     ALTER COLUMN schema_version SET NOT NULL, ALTER COLUMN source_kind SET NOT NULL,
     ADD CONSTRAINT history_provenance CHECK(source_kind='legacy_unverified' OR
      (source_kind='explicit' AND source_draft_id IS NOT NULL
       AND source_draft_revision IS NOT NULL AND source_draft_revision>0
       AND analysis_run_id IS NOT NULL AND saved_by_user_id IS NOT NULL
       AND completed_at IS NOT NULL AND idempotency_key IS NOT NULL AND request_hash IS NOT NULL));
    """)
    for table, column, name, target in (
        ("projects", "user_id", "projects_user_id_users_id_fk", "users"),
        ("drafts", "project_id", "drafts_project_id_projects_id_fk", "projects"),
        ("history_entries", "project_id", "history_entries_project_id_projects_id_fk", "projects"),
        (
            "evaluation_cases",
            "history_entry_id",
            "evaluation_cases_history_entry_id_history_entries_id_fk",
            "history_entries",
        ),
        ("evaluation_cases", "user_id", "evaluation_cases_user_id_users_id_fk", "users"),
    ):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY({column}) "
            f"REFERENCES {target}(id) ON DELETE RESTRICT"
        )
    op.execute("""
    CREATE FUNCTION workflow_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'immutable workflow record' USING ERRCODE='23514'; END $$;
    CREATE TRIGGER immutable_revisions BEFORE UPDATE OR DELETE ON draft_revisions FOR EACH ROW
EXECUTE FUNCTION workflow_immutable();
    CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON history_entries FOR EACH ROW
EXECUTE FUNCTION workflow_immutable();
    CREATE TRIGGER immutable_events BEFORE UPDATE OR DELETE ON activity_events FOR EACH ROW
EXECUTE FUNCTION workflow_immutable();
    CREATE FUNCTION workflow_analysis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
     IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable analysis'; END IF;
     IF
(to_jsonb(NEW)-ARRAY['status','started_at','finished_at','result_snapshot','result_schema_version','request_language','error_code'])
 IS DISTINCT FROM

(to_jsonb(OLD)-ARRAY['status','started_at','finished_at','result_snapshot','result_schema_version','request_language','error_code'])
 OR
        OLD.status IN ('succeeded','failed','cancelled') OR NOT
        ((OLD.status='pending' AND NEW.status='running') OR (OLD.status='running' AND NEW.status
 IN ('succeeded','failed','cancelled')))
     THEN RAISE EXCEPTION 'immutable analysis or invalid transition' USING ERRCODE='23514'; END
IF;
     RETURN NEW;
    END $$;
    CREATE TRIGGER immutable_analysis BEFORE UPDATE OR DELETE ON analysis_runs FOR EACH ROW
EXECUTE FUNCTION workflow_analysis_guard();
    CREATE FUNCTION workflow_agreement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
     IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable agreement'; END IF;
     IF (to_jsonb(NEW)-ARRAY['status','revision','voided_at','updated_at']) IS DISTINCT FROM
(to_jsonb(OLD)-ARRAY['status','revision','voided_at','updated_at']) OR
        OLD.status<>'finalized' OR NEW.status<>'voided' OR NEW.revision<>OLD.revision+1
     THEN RAISE EXCEPTION 'immutable agreement or invalid transition' USING ERRCODE='23514'; END
 IF;
     RETURN NEW;
    END $$;
    CREATE TRIGGER immutable_agreement BEFORE UPDATE OR DELETE ON change_orders FOR EACH ROW
EXECUTE FUNCTION workflow_agreement_guard();
    CREATE FUNCTION workflow_export_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
     IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable export'; END IF;
     IF OLD.status IN ('ready','expired') AND NOT (OLD.status='ready' AND NEW.status='expired'
AND (to_jsonb(NEW)-'status')=(to_jsonb(OLD)-'status'))
     THEN RAISE EXCEPTION 'immutable ready export' USING ERRCODE='23514'; END IF;
     RETURN NEW;
    END $$;
    CREATE TRIGGER immutable_ready_export BEFORE UPDATE OR DELETE ON document_exports FOR EACH
ROW EXECUTE FUNCTION workflow_export_guard();
    """)


def downgrade():
    raise RuntimeError("Retain archives and use a reviewed forward correction")
