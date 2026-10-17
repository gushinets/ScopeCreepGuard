"""Add profiles, explicit ownership and versioned events without rewriting old events."""

from alembic import op

revision = "0006_profile_metrics"
down_revision = "0005_llm_workflow"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE profiles (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
      display_name text, business_name text, provider_name text, profession text,
      status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','inactive')),
      revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
      analytics_excluded boolean NOT NULL DEFAULT false,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(id,user_id), CHECK(updated_at>=created_at)
    );
    CREATE TABLE profile_preferences (
      profile_id uuid PRIMARY KEY REFERENCES profiles(id) ON DELETE RESTRICT,
      locale text CHECK(locale IN ('ru','en')),
      timezone text CHECK(length(timezone) BETWEEN 1 AND 100),
      preferred_tone text CHECK(preferred_tone IN ('warm','neutral','firm')),
      default_currency text CHECK(default_currency IN ('RUB','USD','EUR')),
      revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE FUNCTION profile_preferences_timezone_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.timezone IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM pg_catalog.pg_timezone_names WHERE name=NEW.timezone
      ) THEN RAISE EXCEPTION 'invalid profile timezone' USING ERRCODE='23514'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER profile_preferences_timezone BEFORE INSERT OR UPDATE ON profile_preferences
      FOR EACH ROW EXECUTE FUNCTION profile_preferences_timezone_guard();
    CREATE TABLE profile_revisions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      profile_id uuid NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
      revision bigint NOT NULL CHECK(revision>0),
      snapshot jsonb NOT NULL CHECK(jsonb_typeof(snapshot)='object'),
      actor_user_id uuid NOT NULL,
      operation_id uuid NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(profile_id,revision), UNIQUE(profile_id,operation_id),
      FOREIGN KEY(profile_id,actor_user_id) REFERENCES profiles(id,user_id) ON DELETE RESTRICT
    );
    CREATE TRIGGER immutable_profile_revisions BEFORE UPDATE OR DELETE ON profile_revisions
      FOR EACH ROW EXECUTE FUNCTION workflow_immutable();
    CREATE TABLE product_sessions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      profile_id uuid NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
      browser_key_hash text NOT NULL CHECK(browser_key_hash ~ '^[0-9a-f]{64}$'),
      started_at timestamptz NOT NULL, last_activity_at timestamptz NOT NULL,
      ended_at timestamptz, rule_version integer NOT NULL CHECK(rule_version>0),
      UNIQUE(id,profile_id), CHECK(last_activity_at>=started_at),
      CHECK(ended_at IS NULL OR ended_at>=last_activity_at)
    );
    CREATE INDEX product_sessions_profile_started ON product_sessions(profile_id,started_at);
    CREATE UNIQUE INDEX product_sessions_one_open_browser
      ON product_sessions(profile_id,browser_key_hash) WHERE ended_at IS NULL;
    ALTER TABLE projects ADD COLUMN profile_id uuid,
      ADD CONSTRAINT projects_profile_owner_fk FOREIGN KEY(profile_id,user_id)
        REFERENCES profiles(id,user_id) ON DELETE RESTRICT,
      ADD CONSTRAINT projects_id_profile_unique UNIQUE(id,profile_id);
    CREATE INDEX projects_profile ON projects(profile_id);
    """)
    from scope_guard.database.profile_backfill import backfill_profiles

    backfill_profiles(op.get_bind())
    # NULL extension fields identify historical contracts. Immutable triggers stay enabled.
    op.execute("""
    ALTER TABLE activity_events ALTER COLUMN project_id DROP NOT NULL,
      ADD COLUMN profile_id uuid REFERENCES profiles(id) ON DELETE RESTRICT,
      ADD COLUMN product_session_id uuid,
      ADD COLUMN event_version integer,
      ADD COLUMN source text,
      ADD COLUMN deduplication_key text,
      ADD COLUMN occurred_at timestamptz,
      ADD COLUMN recorded_at timestamptz,
      ADD CONSTRAINT activity_profile_project_fk FOREIGN KEY(project_id,profile_id)
        REFERENCES projects(id,profile_id) ON DELETE RESTRICT,
      ADD CONSTRAINT activity_profile_actor_fk FOREIGN KEY(profile_id,actor_user_id)
        REFERENCES profiles(id,user_id) ON DELETE RESTRICT,
      ADD CONSTRAINT activity_profile_session_fk FOREIGN KEY(product_session_id,profile_id)
        REFERENCES product_sessions(id,profile_id) ON DELETE RESTRICT,
      ADD CONSTRAINT activity_source_dedup_unique UNIQUE(source,deduplication_key),
      ADD CONSTRAINT activity_event_contract CHECK (
        (event_version IS NULL AND profile_id IS NULL AND product_session_id IS NULL
          AND source IS NULL AND deduplication_key IS NULL AND occurred_at IS NULL
          AND recorded_at IS NULL AND project_id IS NOT NULL)
        OR
        (event_version IS NOT NULL AND event_version=2 AND profile_id IS NOT NULL
          AND source IS NOT NULL AND length(btrim(source)) BETWEEN 1 AND 100
          AND deduplication_key IS NOT NULL AND length(btrim(deduplication_key)) BETWEEN 1 AND 250
          AND occurred_at IS NOT NULL AND recorded_at IS NOT NULL AND recorded_at>=occurred_at
          AND actor_type IN ('user','system')
          AND (actor_type='system' OR actor_user_id IS NOT NULL)
          AND payload_version>0 AND jsonb_typeof(payload)='object'
          AND (project_id IS NOT NULL OR (draft_id IS NULL AND draft_revision_id IS NULL
            AND analysis_run_id IS NULL AND history_entry_id IS NULL AND change_order_id IS NULL
            AND document_export_id IS NULL)))
      );
    CREATE INDEX activity_profile_occurred ON activity_events(profile_id,occurred_at);
    ALTER TABLE activity_events DROP CONSTRAINT
      activity_events_project_id_operation_id_event_type_key;
    CREATE UNIQUE INDEX activity_legacy_operation
      ON activity_events(project_id,operation_id,event_type) WHERE event_version IS NULL;
    """)
    op.execute(MARKETING_DDL)


def downgrade():
    raise RuntimeError("Retain profile and behavior facts; use a reviewed forward correction")


MARKETING_DDL = """
CREATE TABLE marketing_metrics (
 report_date date PRIMARY KEY,
 calculated_at timestamptz NOT NULL,
 data_through timestamptz NOT NULL,
 definition_version integer NOT NULL CHECK(definition_version>0),
 is_partial boolean NOT NULL,
 quality_notes jsonb NOT NULL CHECK(jsonb_typeof(quality_notes)='array'),
 ai_calls bigint CHECK(ai_calls>=0),
 ai_retries bigint CHECK(ai_retries>=0),
 input_tokens bigint CHECK(input_tokens>=0),
 output_tokens bigint CHECK(output_tokens>=0),
 cached_tokens bigint CHECK(cached_tokens>=0),
 reasoning_tokens bigint CHECK(reasoning_tokens>=0),
 ai_estimated_cost_usd numeric(20,10) CHECK(ai_estimated_cost_usd>=0),
 ai_cost_unknown_calls bigint CHECK(ai_cost_unknown_calls>=0),
 ai_usage_unknown_calls bigint CHECK(ai_usage_unknown_calls>=0),
 validation_accepted bigint CHECK(validation_accepted>=0),
 validation_rejected bigint CHECK(validation_rejected>=0),
 validation_rejection_percent numeric(9,4) CHECK(validation_rejection_percent BETWEEN 0 AND 100),
 registered_profiles bigint CHECK(registered_profiles>=0),
 new_profiles bigint CHECK(new_profiles>=0),
 dau bigint CHECK(dau>=0),
 mau bigint CHECK(mau>=0),
 activation_eligible_profiles bigint CHECK(activation_eligible_profiles>=0),
 activated_profiles bigint CHECK(activated_profiles>=0),
 ttv_sample_size bigint CHECK(ttv_sample_size>=0),
 pql_profiles bigint CHECK(pql_profiles>=0),
 retention_d7_base bigint CHECK(retention_d7_base>=0),
 retention_d7_returned bigint CHECK(retention_d7_returned>=0),
 retention_d30_base bigint CHECK(retention_d30_base>=0),
 retention_d30_returned bigint CHECK(retention_d30_returned>=0),
 analysis_users bigint CHECK(analysis_users>=0),
 regeneration_users bigint CHECK(regeneration_users>=0),
 translation_users bigint CHECK(translation_users>=0),
 change_order_users bigint CHECK(change_order_users>=0),
 change_orders_created bigint CHECK(change_orders_created>=0),
 change_orders_voided bigint CHECK(change_orders_voided>=0),
 verdict_correct bigint CHECK(verdict_correct>=0),
 verdict_wrong bigint CHECK(verdict_wrong>=0),
 verdict_debatable bigint CHECK(verdict_debatable>=0),
 verdict_evaluated_checks bigint CHECK(verdict_evaluated_checks>=0),
 operations_succeeded bigint CHECK(operations_succeeded>=0),
 operations_failed bigint CHECK(operations_failed>=0),
 operations_cancelled bigint CHECK(operations_cancelled>=0),
 operation_duration_sample_size bigint CHECK(operation_duration_sample_size>=0),
 check_started bigint CHECK(check_started>=0),
 check_succeeded bigint CHECK(check_succeeded>=0),
 check_failed bigint CHECK(check_failed>=0),
 check_cancelled bigint CHECK(check_cancelled>=0),
 check_duration_sample_size bigint CHECK(check_duration_sample_size>=0),
 regeneration_started bigint CHECK(regeneration_started>=0),
 regeneration_succeeded bigint CHECK(regeneration_succeeded>=0),
 regeneration_failed bigint CHECK(regeneration_failed>=0),
 regeneration_cancelled bigint CHECK(regeneration_cancelled>=0),
 regeneration_duration_sample_size bigint CHECK(regeneration_duration_sample_size>=0),
 translation_started bigint CHECK(translation_started>=0),
 translation_succeeded bigint CHECK(translation_succeeded>=0),
 translation_failed bigint CHECK(translation_failed>=0),
 translation_cancelled bigint CHECK(translation_cancelled>=0),
 translation_duration_sample_size bigint CHECK(translation_duration_sample_size>=0),
 estimate_started bigint CHECK(estimate_started>=0),
 estimate_succeeded bigint CHECK(estimate_succeeded>=0),
 estimate_failed bigint CHECK(estimate_failed>=0),
 estimate_cancelled bigint CHECK(estimate_cancelled>=0),
 estimate_duration_sample_size bigint CHECK(estimate_duration_sample_size>=0),
 stickiness_percent numeric(9,4) CHECK(stickiness_percent BETWEEN 0 AND 100),
 activation_rate_percent numeric(9,4) CHECK(activation_rate_percent BETWEEN 0 AND 100),
 retention_d7_percent numeric(9,4) CHECK(retention_d7_percent BETWEEN 0 AND 100),
 retention_d30_percent numeric(9,4) CHECK(retention_d30_percent BETWEEN 0 AND 100),
 analysis_adoption_percent numeric(9,4) CHECK(analysis_adoption_percent BETWEEN 0 AND 100),
 regeneration_adoption_percent numeric(9,4) CHECK(regeneration_adoption_percent BETWEEN 0 AND 100),
 translation_adoption_percent numeric(9,4) CHECK(translation_adoption_percent BETWEEN 0 AND 100),
 change_order_adoption_percent numeric(9,4) CHECK(change_order_adoption_percent BETWEEN 0 AND 100),
 verdict_feedback_percent numeric(9,4) CHECK(verdict_feedback_percent BETWEEN 0 AND 100),
 operation_success_percent numeric(9,4) CHECK(operation_success_percent BETWEEN 0 AND 100),
 check_success_percent numeric(9,4) CHECK(check_success_percent BETWEEN 0 AND 100),
 regeneration_success_percent numeric(9,4) CHECK(regeneration_success_percent BETWEEN 0 AND 100),
 translation_success_percent numeric(9,4) CHECK(translation_success_percent BETWEEN 0 AND 100),
 estimate_success_percent numeric(9,4) CHECK(estimate_success_percent BETWEEN 0 AND 100),
 time_to_value_median_seconds numeric(20,3) CHECK(time_to_value_median_seconds>=0),
 operation_duration_median_ms numeric(20,3) CHECK(operation_duration_median_ms>=0),
 operation_duration_p95_ms numeric(20,3) CHECK(operation_duration_p95_ms>=0),
 check_duration_median_ms numeric(20,3) CHECK(check_duration_median_ms>=0),
 check_duration_p95_ms numeric(20,3) CHECK(check_duration_p95_ms>=0),
 regeneration_duration_median_ms numeric(20,3) CHECK(regeneration_duration_median_ms>=0),
 regeneration_duration_p95_ms numeric(20,3) CHECK(regeneration_duration_p95_ms>=0),
 translation_duration_median_ms numeric(20,3) CHECK(translation_duration_median_ms>=0),
 translation_duration_p95_ms numeric(20,3) CHECK(translation_duration_p95_ms>=0),
 estimate_duration_median_ms numeric(20,3) CHECK(estimate_duration_median_ms>=0),
 estimate_duration_p95_ms numeric(20,3) CHECK(estimate_duration_p95_ms>=0),
 CHECK(data_through<=calculated_at)
);
"""
