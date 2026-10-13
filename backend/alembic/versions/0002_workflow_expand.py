"""Compatible nullable expansion; no existing data is removed."""

from alembic import op

revision = "0002_workflow_expand"
down_revision = "0001_existing_drizzle_schema"
branch_labels = depends_on = None

DDL = """
ALTER TABLE projects ADD COLUMN client_email text, ADD COLUMN end_date date,
 ADD COLUMN updated_at timestamptz, ADD COLUMN archived_at timestamptz,
 ADD COLUMN creation_key uuid, ADD COLUMN creation_request_hash text;
ALTER TABLE projects ADD CONSTRAINT projects_id_owner_unique UNIQUE(id,user_id);
CREATE UNIQUE INDEX projects_owner_creation_key ON projects(user_id,creation_key) WHERE
creation_key IS NOT NULL;
CREATE INDEX projects_owner_listing ON projects(user_id,archived_at,created_at DESC);
ALTER TABLE drafts ALTER COLUMN history_entry_id DROP NOT NULL,
 ALTER COLUMN idempotency_key DROP NOT NULL, ALTER COLUMN analysis_snapshot DROP NOT NULL,
 ALTER COLUMN locale DROP NOT NULL, ALTER COLUMN client_material_language DROP NOT NULL;
ALTER TABLE drafts ADD COLUMN request_text text, ADD COLUMN last_analysis_run_id uuid,
 ADD COLUMN analysis_is_stale boolean, ADD COLUMN revision bigint;
ALTER TABLE drafts ADD CONSTRAINT drafts_id_project_unique UNIQUE(id,project_id);
CREATE UNIQUE INDEX drafts_working_project ON drafts(project_id) WHERE revision IS NOT NULL;
CREATE TABLE draft_revisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), draft_id uuid NOT NULL,
 project_id uuid NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 state_snapshot jsonb NOT NULL, schema_version integer NOT NULL, reason text NOT NULL,
 actor_type text NOT NULL, actor_user_id uuid REFERENCES users(id) ON DELETE RESTRICT,
 operation_id uuid NOT NULL, request_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT
 now(),
 UNIQUE(draft_id,revision), UNIQUE(draft_id,operation_id), UNIQUE(id,project_id),
 FOREIGN KEY(draft_id,project_id) REFERENCES drafts(id,project_id) ON DELETE RESTRICT
);
CREATE TABLE analysis_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL,
 source_draft_id uuid NOT NULL, source_draft_revision bigint NOT NULL
CHECK(source_draft_revision>0),
 requested_by_user_id uuid NOT NULL, request_text text NOT NULL,
 project_snapshot jsonb NOT NULL, interface_locale text NOT NULL,
 requested_document_language text, request_language text, result_snapshot jsonb,
 input_schema_version integer NOT NULL, result_schema_version integer,
 status text NOT NULL CHECK(status IN ('pending','running','succeeded','failed','cancelled')),
 model text, prompt_version text, error_code text, idempotency_key uuid NOT NULL,
 request_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 started_at timestamptz, finished_at timestamptz,
 UNIQUE(id,project_id), UNIQUE(id,requested_by_user_id), UNIQUE(project_id,idempotency_key),
 FOREIGN KEY(project_id,requested_by_user_id) REFERENCES projects(id,user_id) ON DELETE
RESTRICT,
 FOREIGN KEY(source_draft_id,project_id) REFERENCES drafts(id,project_id) ON DELETE RESTRICT,
 FOREIGN KEY(source_draft_id,source_draft_revision) REFERENCES
draft_revisions(draft_id,revision) ON DELETE RESTRICT,
 CHECK(status<>'succeeded' OR (result_snapshot IS NOT NULL AND result_schema_version IS NOT NULL
 AND finished_at IS NOT NULL))
);
CREATE INDEX analysis_runs_processing ON analysis_runs(status,started_at);
ALTER TABLE drafts ADD CONSTRAINT drafts_analysis_project_fk FOREIGN
KEY(last_analysis_run_id,project_id) REFERENCES analysis_runs(id,project_id) ON DELETE RESTRICT;
ALTER TABLE history_entries ADD COLUMN source_draft_id uuid, ADD COLUMN source_draft_revision
bigint,
 ADD COLUMN analysis_run_id uuid, ADD COLUMN check_snapshot jsonb, ADD COLUMN schema_version
integer,
 ADD COLUMN completed_at timestamptz, ADD COLUMN saved_by_user_id uuid,
 ADD COLUMN source_kind text, ADD COLUMN idempotency_key uuid, ADD COLUMN request_hash text;
ALTER TABLE history_entries ADD CONSTRAINT history_id_project_unique UNIQUE(id,project_id),
 ADD CONSTRAINT history_source_project_fk FOREIGN KEY(source_draft_id,project_id) REFERENCES
drafts(id,project_id) ON DELETE RESTRICT,
 ADD CONSTRAINT history_source_revision_fk FOREIGN KEY(source_draft_id,source_draft_revision)
REFERENCES draft_revisions(draft_id,revision) ON DELETE RESTRICT,
 ADD CONSTRAINT history_analysis_project_fk FOREIGN KEY(analysis_run_id,project_id) REFERENCES
analysis_runs(id,project_id) ON DELETE RESTRICT,
 ADD CONSTRAINT history_saving_owner_fk FOREIGN KEY(project_id,saved_by_user_id) REFERENCES
projects(id,user_id) ON DELETE RESTRICT;
CREATE UNIQUE INDEX history_operation ON history_entries(project_id,idempotency_key) WHERE
idempotency_key IS NOT NULL;
CREATE INDEX history_project_listing ON history_entries(project_id,date DESC,id);
CREATE TABLE change_orders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL,
 history_entry_id uuid NOT NULL, reference text NOT NULL UNIQUE,
 content_snapshot jsonb NOT NULL, schema_version integer NOT NULL,
 status text NOT NULL CHECK(status IN ('finalized','voided')),
 revision bigint NOT NULL CHECK(revision>0), finalized_by_user_id uuid NOT NULL,
 finalized_at timestamptz NOT NULL DEFAULT now(), voided_at timestamptz,
 idempotency_key uuid NOT NULL, request_hash text NOT NULL, updated_at timestamptz NOT NULL
DEFAULT now(),
 UNIQUE(id,project_id), UNIQUE(history_entry_id,idempotency_key),
 FOREIGN KEY(history_entry_id,project_id) REFERENCES history_entries(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(project_id,finalized_by_user_id) REFERENCES projects(id,user_id) ON DELETE
RESTRICT,
 CHECK((status='voided')=(voided_at IS NOT NULL))
);
CREATE UNIQUE INDEX change_orders_active ON change_orders(history_entry_id) WHERE
status='finalized';
CREATE TABLE document_exports (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL,
 change_order_id uuid NOT NULL, requested_by_user_id uuid NOT NULL,
 format text NOT NULL CHECK(format='pdf'), language text NOT NULL,
 renderer_version text NOT NULL, template_version text NOT NULL,
 status text NOT NULL CHECK(status IN ('pending','processing','ready','failed','expired')),
 object_key text UNIQUE, checksum text, mime_type text, size_bytes bigint CHECK(size_bytes>=0),
error_code text,
 attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count>=0), lease_expires_at timestamptz,
 idempotency_key uuid NOT NULL, request_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 UNIQUE(id,project_id), UNIQUE(change_order_id,idempotency_key),
 FOREIGN KEY(change_order_id,project_id) REFERENCES change_orders(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(project_id,requested_by_user_id) REFERENCES projects(id,user_id) ON DELETE
RESTRICT,
 CHECK(status<>'ready' OR (object_key IS NOT NULL AND checksum IS NOT NULL AND mime_type IS NOT
NULL AND size_bytes IS NOT NULL AND finished_at IS NOT NULL))
);
CREATE INDEX document_exports_pending ON document_exports(status,lease_expires_at,created_at)
WHERE status IN ('pending','processing','failed');
CREATE TABLE activity_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id)
 ON DELETE RESTRICT,
 draft_id uuid, draft_revision_id uuid, analysis_run_id uuid, history_entry_id uuid,
 change_order_id uuid, document_export_id uuid, actor_type text NOT NULL,
 actor_user_id uuid, event_type text NOT NULL, operation_id uuid NOT NULL,
 payload jsonb NOT NULL, payload_version integer NOT NULL, created_at timestamptz NOT NULL
DEFAULT now(),
 UNIQUE(project_id,operation_id,event_type),
 FOREIGN KEY(draft_id,project_id) REFERENCES drafts(id,project_id) ON DELETE RESTRICT,
 FOREIGN KEY(draft_revision_id,project_id) REFERENCES draft_revisions(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(analysis_run_id,project_id) REFERENCES analysis_runs(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(history_entry_id,project_id) REFERENCES history_entries(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(change_order_id,project_id) REFERENCES change_orders(id,project_id) ON DELETE
RESTRICT,
 FOREIGN KEY(document_export_id,project_id) REFERENCES document_exports(id,project_id) ON DELETE
 RESTRICT,
 FOREIGN KEY(project_id,actor_user_id) REFERENCES projects(id,user_id) ON DELETE RESTRICT
);
CREATE INDEX activity_project_date ON activity_events(project_id,created_at DESC);
ALTER TABLE evaluation_cases ADD COLUMN analysis_run_id uuid;
ALTER TABLE evaluation_cases ADD CONSTRAINT evaluation_analysis_owner_fk FOREIGN
KEY(analysis_run_id,user_id) REFERENCES analysis_runs(id,requested_by_user_id) ON DELETE
RESTRICT;
CREATE UNIQUE INDEX evaluations_analysis_user ON evaluation_cases(analysis_run_id,user_id) WHERE
 analysis_run_id IS NOT NULL;
"""


def upgrade():
    op.execute(DDL)
    for table, columns in (
        ("draft_revisions", ("project_id", "actor_user_id")),
        ("analysis_runs", ("project_id", "source_draft_id", "requested_by_user_id")),
        ("history_entries", ("source_draft_id", "analysis_run_id", "saved_by_user_id")),
        ("change_orders", ("project_id", "history_entry_id", "finalized_by_user_id")),
        ("document_exports", ("project_id", "change_order_id", "requested_by_user_id")),
        (
            "activity_events",
            (
                "draft_id",
                "draft_revision_id",
                "analysis_run_id",
                "history_entry_id",
                "change_order_id",
                "document_export_id",
                "actor_user_id",
            ),
        ),
    ):
        for column in columns:
            op.execute(f"CREATE INDEX {table}_{column}_idx ON {table}({column})")


def downgrade():
    raise RuntimeError("Workflow data is retained; use a reviewed forward correction")
