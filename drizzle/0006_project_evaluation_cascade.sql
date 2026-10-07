ALTER TABLE "evaluation_cases" DROP CONSTRAINT "evaluation_cases_history_entry_id_history_entries_id_fk";
--> statement-breakpoint
ALTER TABLE "evaluation_cases" ADD CONSTRAINT "evaluation_cases_history_entry_id_history_entries_id_fk" FOREIGN KEY ("history_entry_id") REFERENCES "public"."history_entries"("id") ON DELETE cascade ON UPDATE no action;