"""Immutable baseline of Drizzle 0000вЂ“0006. Do not import mutable ORM metadata."""

from alembic import op

revision = "0001_existing_drizzle_schema"
down_revision = None
branch_labels = None
depends_on = None

DDL = """
CREATE TYPE public.industry AS ENUM ('Development','Design','Marketing');
CREATE TYPE public.verdict AS ENUM ('in_scope','borderline','out_of_scope');
CREATE TYPE public.pricing_model AS ENUM ('hourly','fixed');
CREATE TYPE public.currency AS ENUM ('RUB','USD','EUR');
CREATE TYPE public.evaluation_accuracy AS ENUM ('correct','wrong','debatable');
CREATE TABLE public.users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
 email text NOT NULL, password_hash text NOT NULL, created_at timestamptz DEFAULT now() NOT NULL,
 CONSTRAINT users_email_unique UNIQUE(email)
);
CREATE TABLE public.projects (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL, user_id uuid NOT NULL,
 name text NOT NULL, client text, industry public.industry NOT NULL, scope text NOT NULL,
 start_date date, pricing_model public.pricing_model, currency public.currency,
 hourly_rate numeric(14,2), fixed_price numeric(14,2), last_checked date,
 created_at timestamptz DEFAULT now() NOT NULL,
 CONSTRAINT projects_user_id_users_id_fk FOREIGN KEY(user_id) REFERENCES public.users(id) ON
DELETE CASCADE ON UPDATE NO ACTION,
 CONSTRAINT projects_commercial_terms_consistent CHECK (
  (start_date IS NULL AND pricing_model IS NULL AND currency IS NULL AND hourly_rate IS NULL AND
fixed_price IS NULL)
  OR (start_date IS NOT NULL AND currency IS NOT NULL AND (
   (pricing_model='hourly' AND hourly_rate>0 AND fixed_price IS NULL)
   OR (pricing_model='fixed' AND fixed_price>0 AND hourly_rate IS NULL)))
 )
);
CREATE TABLE public.history_entries (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL, project_id uuid NOT NULL,
 date date NOT NULL, request text NOT NULL, verdict public.verdict NOT NULL, summary text NOT NULL,
 CONSTRAINT history_entries_project_id_projects_id_fk FOREIGN KEY(project_id) REFERENCES
public.projects(id) ON DELETE CASCADE ON UPDATE NO ACTION
);
CREATE TABLE public.drafts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL, project_id uuid NOT NULL,
 history_entry_id uuid NOT NULL, idempotency_key uuid NOT NULL, project_snapshot jsonb,
 analysis_snapshot jsonb NOT NULL, draft_document jsonb NOT NULL, locale text NOT NULL,
 request_language text, client_material_language text NOT NULL, change_order_labels jsonb,
 status text DEFAULT 'draft' NOT NULL, created_at timestamptz DEFAULT now() NOT NULL,
 updated_at timestamptz DEFAULT now() NOT NULL,
 CONSTRAINT drafts_history_entry_id_unique UNIQUE(history_entry_id),
 CONSTRAINT drafts_project_id_projects_id_fk FOREIGN KEY(project_id) REFERENCES
public.projects(id) ON DELETE CASCADE ON UPDATE NO ACTION,
 CONSTRAINT drafts_history_entry_id_history_entries_id_fk FOREIGN KEY(history_entry_id)
REFERENCES public.history_entries(id) ON DELETE CASCADE ON UPDATE NO ACTION,
 CONSTRAINT drafts_status_valid CHECK(status='draft'),
 CONSTRAINT drafts_locale_valid CHECK(locale IN ('ru','en'))
);
CREATE UNIQUE INDEX drafts_project_creation_key_unique ON public.drafts USING
btree(project_id,idempotency_key);
CREATE INDEX drafts_project_created_at_idx ON public.drafts USING btree(project_id,created_at);
CREATE TABLE public.evaluation_cases (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL, user_id uuid NOT NULL,
 history_entry_id uuid, scope text NOT NULL, request text NOT NULL,
 ai_verdict public.verdict NOT NULL, human_verdict public.verdict, ai_reasoning text NOT NULL,
 accuracy public.evaluation_accuracy NOT NULL, industry public.industry NOT NULL,
 created_at timestamptz DEFAULT now() NOT NULL, updated_at timestamptz DEFAULT now() NOT NULL,
 CONSTRAINT evaluation_cases_history_entry_id_unique UNIQUE(history_entry_id),
 CONSTRAINT evaluation_cases_user_id_users_id_fk FOREIGN KEY(user_id) REFERENCES
public.users(id) ON DELETE CASCADE ON UPDATE NO ACTION,
 CONSTRAINT evaluation_cases_history_entry_id_history_entries_id_fk FOREIGN
KEY(history_entry_id) REFERENCES public.history_entries(id) ON DELETE CASCADE ON UPDATE NO
ACTION,
 CONSTRAINT evaluation_cases_accuracy_human_verdict CHECK (
  (accuracy='debatable' AND human_verdict IS NULL)
  OR (accuracy='correct' AND human_verdict IS NOT NULL AND human_verdict=ai_verdict)
  OR (accuracy='wrong' AND human_verdict IS NOT NULL AND human_verdict<>ai_verdict)
 )
);
"""


def upgrade():
    for statement in DDL.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    raise RuntimeError(
        "Destructive baseline downgrade refused; use reviewed backup/restore recovery"
    )
