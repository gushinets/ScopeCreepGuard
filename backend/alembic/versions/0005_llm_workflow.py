"""Add bounded durable LLM execution; existing ANY-549 records remain unchanged."""

from alembic import op

revision = "0005_llm_workflow"
down_revision = "0004_workflow_retire"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE llm_operations (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      owner_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      draft_id uuid NOT NULL REFERENCES drafts(id) ON DELETE RESTRICT,
      source_revision bigint NOT NULL CHECK(source_revision>0),
      analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE RESTRICT,
      kind text NOT NULL CHECK(kind IN ('check','regenerate','translate','estimate')),
      command_key uuid NOT NULL, request_hash text NOT NULL,
      frozen_input jsonb NOT NULL, input_hash text NOT NULL, policy jsonb NOT NULL,
      status text NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued','running','succeeded','failed')),
      created_at timestamptz NOT NULL DEFAULT now(), deadline_at timestamptz NOT NULL,
      worker_id text, lease_expires_at timestamptz, epoch bigint NOT NULL DEFAULT 0,
      physical_calls integer NOT NULL DEFAULT 0 CHECK(physical_calls>=0),
      spent numeric(20,10) NOT NULL DEFAULT 0 CHECK(spent>=0),
      reserved numeric(20,10) NOT NULL DEFAULT 0 CHECK(reserved>=0),
      result jsonb, error jsonb, finished_at timestamptz,
      UNIQUE(owner_id,project_id,command_key),
      CHECK(status<>'succeeded' OR (result IS NOT NULL AND finished_at IS NOT NULL))
    );
    CREATE INDEX llm_operations_queue ON llm_operations(status,lease_expires_at,created_at);
    CREATE TABLE llm_steps (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      operation_id uuid NOT NULL REFERENCES llm_operations(id) ON DELETE RESTRICT,
      stage_key text NOT NULL, input_hash text NOT NULL,
      prompt_version text NOT NULL, schema_version text NOT NULL,
      status text NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','running','accepted','failed')),
      semantic_attempt integer NOT NULL DEFAULT 0 CHECK(semantic_attempt BETWEEN 0 AND 3),
      transport_attempt integer NOT NULL DEFAULT 0 CHECK(transport_attempt BETWEEN 0 AND 2),
      prepared_request jsonb, candidate text, feedback jsonb, accepted_result jsonb,
      UNIQUE(operation_id,stage_key),
      CHECK(status<>'accepted' OR accepted_result IS NOT NULL)
    );
    CREATE TABLE provider_calls (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      operation_id uuid NOT NULL REFERENCES llm_operations(id) ON DELETE RESTRICT,
      step_id uuid NOT NULL REFERENCES llm_steps(id) ON DELETE RESTRICT,
      physical_index integer NOT NULL CHECK(physical_index>0),
      semantic_attempt integer NOT NULL CHECK(semantic_attempt BETWEEN 1 AND 3),
      transport_attempt integer NOT NULL CHECK(transport_attempt BETWEEN 1 AND 2),
      epoch bigint NOT NULL, requested_model text NOT NULL, reasoning_effort text NOT NULL,
      request_hash text NOT NULL,
      actual_model text, actual_provider text, response_id text, provider_request_id text,
      output_status text,
      validation_status text CHECK(validation_status IN ('accepted','rejected')),
      status text NOT NULL CHECK(status IN ('in_flight','completed','failed','unknown')),
      input_tokens integer CHECK(input_tokens>=0), output_tokens integer CHECK(output_tokens>=0),
      cached_tokens integer CHECK(cached_tokens>=0),
      reasoning_tokens integer CHECK(reasoning_tokens>=0),
      reported_cost numeric(20,10) CHECK(reported_cost>=0),
      estimated_cost numeric(20,10) CHECK(estimated_cost>=0),
      reserved_cost numeric(20,10) NOT NULL CHECK(reserved_cost>=0),
      cost_currency text NOT NULL DEFAULT 'USD', cost_status text NOT NULL DEFAULT 'unknown',
      usage_status text NOT NULL DEFAULT 'unknown', error jsonb,
      started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz, latency_ms integer,
      UNIQUE(operation_id,physical_index), UNIQUE(step_id,semantic_attempt,transport_attempt)
    );
    """)


def downgrade():
    raise RuntimeError("Retain provider-call accounting; use a reviewed forward correction")
