CREATE TABLE "drafts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"project_id" uuid NOT NULL,
	"history_entry_id" uuid NOT NULL,
	"idempotency_key" uuid NOT NULL,
	"analysis_snapshot" jsonb NOT NULL,
	"draft_document" jsonb NOT NULL,
	"locale" text NOT NULL,
	"request_language" text,
	"client_material_language" text NOT NULL,
	"change_order_labels" jsonb,
	"status" text DEFAULT 'draft' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "drafts_history_entry_id_unique" UNIQUE("history_entry_id"),
	CONSTRAINT "drafts_status_valid" CHECK ("drafts"."status" = 'draft'),
	CONSTRAINT "drafts_locale_valid" CHECK ("drafts"."locale" IN ('ru', 'en'))
);
--> statement-breakpoint
ALTER TABLE "drafts" ADD CONSTRAINT "drafts_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "drafts" ADD CONSTRAINT "drafts_history_entry_id_history_entries_id_fk" FOREIGN KEY ("history_entry_id") REFERENCES "public"."history_entries"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "drafts_project_creation_key_unique" ON "drafts" USING btree ("project_id","idempotency_key");--> statement-breakpoint
CREATE INDEX "drafts_project_created_at_idx" ON "drafts" USING btree ("project_id","created_at");